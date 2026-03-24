"""
High-level API functions for SQL analysis and visualization.

This module provides convenience functions that orchestrate the core classes
(SqlHelper, DagGraph, ColumnLineageExtractor) to perform common tasks:
- Reading SQL from files
- Extracting source/target tables
- Building and visualizing table dependency DAGs
- Finding root and leaf tables

Example:
    from src.utils import get_all_source_tables, __visualize_dag

    # Get all source tables from SQL
    sql = "SELECT * FROM t1; INSERT INTO t2 SELECT * FROM t1;"
    tables = get_all_source_tables(sql)

    # Visualize DAG
    __visualize_dag(sql, "output.html", "My DAG")
"""

import json
import re
from pathlib import Path
from typing import List, Literal, Tuple, Union

from .core.graph import DagGraph, NodeNotFoundException
from .core.helper import get_source_target_tables, split_sql, trim_comment

SearchResult = Union[Tuple[List[str], DagGraph], NodeNotFoundException]


def read_sql_from_directory(path: str | Path) -> str:
    """
    从目录或单个SQL文件中读取SQL内容

    Args:
        dir_path: 目录路径或SQL文件路径

    Returns:
        合并后的SQL字符串
    """
    path = Path(path)
    # 判断文件目录是否存在
    if not path.exists():
        raise FileNotFoundError(f"File or directory not found: {path}")

    # 如果是单个SQL文件，直接读取
    if path.is_file():
        sql_str = path.read_text(encoding="utf-8")
        return sql_str

    # 如果是目录，递归查找所有SQL文件
    sql_files = list(path.rglob("*.sql"))

    # 方式1: 使用字符串拼接
    sql_stmt_str = ""
    for sql_file in sql_files:
        sql_str = sql_file.read_text(encoding="utf-8")
        # 去除注释
        sql_str = trim_comment(sql_str)
        if not sql_str.strip().endswith(";"):
            sql_str += ";\n"
        sql_stmt_str += sql_str

    # 方式2: 使用 StringIO (代码已注释,保留作为参考, 无明显性能提升)
    # import io
    # buf = io.StringIO()
    # for sql_file in sql_files:
    #     sql_str = sql_file.read_text(encoding="utf-8")
    #      # 去除注释
    #     sql_str = trim_comment(sql_str)
    #     if not sql_str.strip().endswith(";"):
    #         sql_str += ";\n"
    #     buf.write(sql_str)
    # sql_stmt_str = buf.getvalue()
    # buf.close()

    return sql_stmt_str


def __build_tables_and_graph(sql_stmt_str: str) -> Tuple[list, list, DagGraph]:
    """
    一次性构建源表、目标表和DAG图，避免重复遍历

    Args:
        sql_stmt_str: SQL语句字符串

    Returns:
        (源表集合, 目标表集合, DAG图对象)
    """
    sql_stmt_lst = split_sql(sql_stmt_str)
    source_tables = set()
    target_tables = set()
    dg = DagGraph()

    for sql_stmt in sql_stmt_lst:
        table_info = get_source_target_tables(sql_stmt)
        if table_info:
            sources = [re.sub(r"`|\"", "", t) for t in table_info["source_tables"]]
            targets = [re.sub(r"`|\"", "", t) for t in table_info["target_tables"]]
            source_tables.update(sources)
            target_tables.update(targets)
            for src in sources:
                for tgt in targets:
                    dg.add_edge(src, tgt)

    return list(source_tables), list(target_tables), dg


def get_all_dag(sql_stmt_str: str) -> DagGraph:
    return __build_tables_and_graph(sql_stmt_str)[2]


def get_all_tables(sql_stmt_str: str) -> List[str]:
    """
    获取所有表名

    Args:
        sql_stmt_str: SQL语句字符串

    Returns:
        所有表名列表
    """
    source_tables, target_tables, _ = __build_tables_and_graph(sql_stmt_str)
    return sorted(list(set(source_tables + target_tables)))


def get_all_root_tables(sql_stmt_str: str) -> List[str]:
    """
    获取所有根表(没有上游写入的表)

    在依赖关系图中,根表是指只被读取但不被写入的表(如ODS层表)

    Example:
        如果有: A -> B, A -> C, B -> D
        则根表为: A (只作为源,不作为目标)

    Args:
        sql_stmt_str: SQL语句字符串

    Returns:
        根表列表(按字母排序)
    """
    source_tables, target_tables, _ = __build_tables_and_graph(sql_stmt_str)
    return sorted(list(set(source_tables) - set(target_tables)))


def get_all_leaf_tables(sql_stmt_str: str) -> List[str]:
    """
    获取所有叶子表(没有下游读取的表)

    在依赖关系图中,叶子表是指只被写入但不被读取的表(如ADS层表)

    Example:
        如果有: A -> B, B -> C, D -> C
        则叶子表为: C (只作为目标,不作为源)

    Args:
        sql_stmt_str: SQL语句字符串

    Returns:
        叶子表列表(按字母排序)
    """
    source_tables, target_tables, _ = __build_tables_and_graph(sql_stmt_str)
    return sorted(list(set(target_tables) - set(source_tables)))


def search_related_root_tables(sql_stmt_str: str, target_table: str) -> SearchResult:
    """
    从目标表向上追溯,获取该依赖路径上的所有根表

    在子图中,根表是指只作为源但不作为目标的表

    Example:
        如果有: A -> B -> C, D -> E, B -> E
        对表 E 执行:
        - 返回: [A, D] (A和B的根是A, E的上游根是A和D)

    Args:
        sql_stmt_str: SQL语句字符串
        target_table: 目标表名

    Returns:
        (根表列表, 上游依赖子图)
    """
    _, _, dg = __build_tables_and_graph(sql_stmt_str)
    related_graph = dg.find_upstream(target_table)
    if isinstance(related_graph, DagGraph):
        if related_graph.empty:
            return [], DagGraph()

        source_tables = set(edge[0] for edge in related_graph.get_edges())
        target_tables = set(edge[1] for edge in related_graph.get_edges())
        return sorted(list(source_tables - target_tables)), related_graph
    else:
        return related_graph


def search_related_upstream_tables(sql_stmt_str: str, target_table: str) -> SearchResult:
    """
    从目标表向上追溯,获取所有上游依赖表(包含所有中间表)

    Example:
        如果有: A -> B -> C, D -> B
        对表 C 执行:
        - 返回: [A, B, D] (C的所有上游: B, A, D)

    Args:
        sql_stmt_str: SQL语句字符串
        target_table: 目标表名

    Returns:
        (上游表列表, 上游依赖子图)
    """
    _, _, dg = __build_tables_and_graph(sql_stmt_str)
    related_graph = dg.find_upstream(target_table)
    if isinstance(related_graph, DagGraph):
        if related_graph.empty:
            return [], DagGraph()

        related_tables = set()
        for node in related_graph.get_nodes():
            related_tables.add(node)

        related_tables.remove(target_table)
        return sorted(list(related_tables)), related_graph
    else:
        return related_graph


def search_related_downstream_tables(sql_stmt_str: str, target_table: str) -> SearchResult:
    """
    从目标表向下追溯,获取所有下游依赖表(包含所有中间表)

    Example:
        如果有: A -> B -> C, B -> D
        对表 A 执行:
        - 返回: [B, C, D] (A的所有下游: B, C, D)

    Args:
        sql_stmt_str: SQL语句字符串
        target_table: 目标表名

    Returns:
        (下游表列表, 下游依赖子图)
    """
    _, _, dg = __build_tables_and_graph(sql_stmt_str)
    related_graph = dg.find_downstream(target_table)
    if isinstance(related_graph, DagGraph):
        if related_graph.empty:
            return [], DagGraph()

        related_tables = set()
        for node in related_graph.get_nodes():
            related_tables.add(node)
        # 移除目标表,避免重复
        related_tables.remove(target_table)
        return sorted(list(related_tables)), related_graph
    else:
        return related_graph


def search_related_tables(sql_stmt_str: str, target_table: str) -> SearchResult:
    """
    从目标表双向追溯,获取所有相关表(上游+下游,不包含自身)

    Example:
        如果有: A -> B -> C, D -> B, C -> E
        对表 B 执行:
        - 返回: [A, C, D, E] (上游: A, D; 下游: C, E)

    Args:
        sql_stmt_str: SQL语句字符串
        target_table: 目标表名

    Returns:
        (相关表列表, 完整依赖子图)
    """
    _, _, dg = __build_tables_and_graph(sql_stmt_str)
    related_graph_upstream = dg.find_upstream(target_table)
    if isinstance(related_graph_upstream, DagGraph):
        related_graph_downstream = dg.find_downstream(target_table)
        if isinstance(related_graph_downstream, DagGraph):
            new_graph = related_graph_downstream.union(related_graph_upstream)

            if new_graph.empty:
                return [], DagGraph()
            else:
                related_tables = set()
                for node in new_graph.get_nodes():
                    related_tables.add(node)
                # 移除目标表,避免重复
                related_tables.remove(target_table)
                return sorted(list(related_tables)), new_graph
        else:
            return related_graph_downstream
    else:
        return related_graph_upstream


def visualize_dag(
    dag_graph: DagGraph, filename: str | Path = "lineage_mermaid.html", template_type: Literal["mermaid", "dagre"] = "mermaid"
) -> None:
    import webbrowser

    html_content = dag_graph.to_html(template_type=template_type)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    abs_path = Path(filename).absolute()
    webbrowser.open(f"file://{abs_path}")
    print(f"HTML文件已生成并打开: {abs_path}")


def list_command_json(tables: list[str], sub_command_arg: str | None = None) -> str:
    result = {
        "status": "ok",
        "command": "list-tables",
        "sub_command_arg": sub_command_arg,
        "tables": tables,
        "meta": {"table_count": len(tables)},
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


def list_command_text(tables: list[str]) -> str:
    if not tables:
        return "未找到相关表, 目标表已经是叶子表或根表"
    result = "- " + "\n- ".join(sorted(tables))
    return result


def search_command_json(search_result: SearchResult, sub_command_arg: str | None = None) -> str:
    result = {
        "status": "ok",
        "command": "search-table",
        "sub_command_arg": sub_command_arg,
        "data": [],
        "meta": {"node_count": 0},
    }
    if isinstance(search_result, Tuple):
        dag_graph = search_result[1]
        dag_dict = dag_graph.to_dict()
        result["data"] = {"nodes": dag_dict.get("nodes"), "edges": dag_dict.get("edges")}
        result["mermaid"] = dag_graph.to_mermaid()
        result["meta"]["node_count"] = dag_dict.get("node_count")
    else:
        result["status"] = str(search_result)

    return json.dumps(result, indent=2, ensure_ascii=False)


def search_command_text(search_result: SearchResult) -> str:

    if isinstance(search_result, Tuple):
        related_tables = search_result[0]
        if not related_tables:
            return "=> 未找到相关表, 目标表已经是叶子表或根表"
        else:
            return "- " + "\n- ".join(sorted(related_tables))
    else:
        return str(search_result)
