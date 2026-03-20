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

import os
import re
from pathlib import Path
from typing import List, Tuple

from .core.graph import DagGraph
from .core.helper import SqlHelper


def read_sql_from_directory(path: str | Path) -> str:
    """
    从目录或单个SQL文件中读取SQL内容

    Args:
        dir_path: 目录路径或SQL文件路径

    Returns:
        合并后的SQL字符串
    """
    path = Path(path)

    # 如果是单个SQL文件，直接读取
    if path.is_file():
        sql_str = path.read_text(encoding="utf-8")
        return sql_str

    # 如果是目录，递归查找所有SQL文件
    sql_files = list(path.rglob("*.sql"))

    sql_stmt_str = ""
    for sql_file in sql_files:
        sql_str = sql_file.read_text(encoding="utf-8")
        if not sql_str.strip().endswith(";"):
            sql_str += ";\n"
        sql_stmt_str += sql_str
    return sql_stmt_str


def __build_tables_and_graph(sql_stmt_str: str) -> Tuple[set, set, DagGraph]:
    """
    一次性构建源表、目标表和DAG图，避免重复遍历

    Args:
        sql_stmt_str: SQL语句字符串

    Returns:
        (源表集合, 目标表集合, DAG图对象)
    """
    sql_stmt_lst = SqlHelper.split(sql_stmt_str)
    helper = SqlHelper()
    source_tables = set()
    target_tables = set()
    dg = DagGraph()

    for sql_stmt in sql_stmt_lst:
        table_info = helper.get_source_target_tables(sql_stmt)
        if table_info:
            sources = [re.sub(r"`|\"", "", t) for t in table_info["source_tables"]]
            targets = [re.sub(r"`|\"", "", t) for t in table_info["target_tables"]]
            source_tables.update(sources)
            target_tables.update(targets)
            for src in sources:
                for tgt in targets:
                    dg.add_edge(src, tgt)

    return source_tables, target_tables, dg


def get_all_tables(sql_stmt_str: str) -> List[str]:
    """
    获取所有表名

    Args:
        sql_stmt_str: SQL语句字符串

    Returns:
        所有表名列表
    """
    source_tables, target_tables, _ = __build_tables_and_graph(sql_stmt_str)
    return sorted(list(source_tables.union(target_tables)))


def get_all_root_tables(sql_stmt_str: str) -> List[str]:
    """
    获取没有上游写入的底表，比如ods表，没有写入任务的表

    Args:
        sql_stmt_str: SQL语句字符串

    Returns:
        根表列表
    """
    source_tables, target_tables, _ = __build_tables_and_graph(sql_stmt_str)
    return sorted(list(source_tables - target_tables))


def search_related_root_tables(sql_stmt_str: str, target_table: str) -> List[str] | None:
    """
    从目标表向上追溯，获取最源头的表（第一层上游根表）

    Args:
        sql_stmt_str: SQL语句字符串
        target_table: 目标表名

    Returns:
        最源头表列表
    """
    _, _, dg = __build_tables_and_graph(sql_stmt_str)
    related_graph = dg.find_upstream(target_table)
    if not related_graph:
        return None

    source_tables = set(edge[0] for edge in related_graph.get_edges())
    target_tables = set(edge[1] for edge in related_graph.get_edges())
    return sorted(list(source_tables - target_tables))


def search_related_upstream_tables(sql_stmt_str: str, target_table: str) -> List[str] | None:
    """
    从目标表向上追溯，获取所有上游相关表（包含中间表）

    Args:
        sql_stmt_str: SQL语句字符串
        target_table: 目标表名

    Returns:
        上游相关表列表
    """
    _, _, dg = __build_tables_and_graph(sql_stmt_str)
    related_graph = dg.find_upstream(target_table)
    if not related_graph:
        return None

    related_tables = set()
    for edge in related_graph.get_edges():
        related_tables.update(edge)

    return sorted(list(related_tables))


def search_related_tables(sql_stmt_str: str, target_table: str) -> List[str] | None:
    _, _, dg = __build_tables_and_graph(sql_stmt_str)
    related_graph_upstream = dg.find_upstream(target_table)
    related_graph_downstream = dg.find_downstream(target_table)
    if not related_graph_upstream or not related_graph_downstream:
        return None
    related_tables = set()
    for edge in related_graph_upstream.get_edges():
        related_tables.update(edge)
    for edge in related_graph_downstream.get_edges():
        related_tables.update(edge)
    return sorted(list(related_tables))


def get_all_leaf_tables(sql_stmt_str: str) -> List[str]:
    """
    获取没有下游任务的目标表，比如ads表，最下游的表

    Args:
        sql_stmt_str: SQL语句字符串

    Returns:
        叶子表列表
    """
    source_tables, target_tables, _ = __build_tables_and_graph(sql_stmt_str)
    return sorted(list(target_tables - source_tables))


def __visualize_dag(dag_graph: DagGraph, filename: str = "dag_mermaid.html") -> None:
    """
    可视化DAG图

    Args:
        sql_stmt_str: SQL语句字符串
    """
    import webbrowser

    html_content = dag_graph.to_html()

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    abs_path = os.path.abspath(filename)
    webbrowser.open(f"file://{abs_path}")
    print(f"Mermaid.js HTML文件已生成并打开: {abs_path}")
