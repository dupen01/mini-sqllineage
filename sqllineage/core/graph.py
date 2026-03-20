"""
DAG (Directed Acyclic Graph) implementation for table dependency tracking.

This module provides a graph data structure for representing and analyzing
table dependencies in SQL queries, with support for:
- Node and edge management
- Upstream/downstream traversal
- Cycle detection
- Mermaid.js format visualization

Example:
    from src.graph import DagGraph

    dg = DagGraph()
    dg.add_edge("table_a", "table_b")
    dg.add_edge("table_b", "table_c")
    dg.print_all_edges_to_mermaid()
"""

import json
from pathlib import Path
from string import Template


class NodeNotFoundException(Exception):
    """Exception raised when a node is not found in the graph."""

    pass


class NodeExistsException(Exception):
    """Exception raised when attempting to add a node that already exists."""

    pass


class CycleDetectedException(Exception):
    """Exception raised when a cycle is detected in the graph."""

    pass


class DagGraph:
    def __init__(self, nodes: list[str] | None = None, edges: list[tuple[str, str]] | None = None) -> None:
        """
        初始化DAG图

        Args:
            nodes: 初始节点列表，默认为空列表
        """
        if nodes is None:
            nodes = []
        self.__nodes = set(nodes)  # 使用集合提升查找效率
        if edges is None:
            # edges = []
            self.__edges = set()  # 使用集合存储边
        else:
            self.__edges = set(edges)  # 使用集合存储边
            self.__nodes.update({node for edge in edges for node in edge})  # 从边中提取节点并添加到节点集合

        self.__adjacency_list: dict[str, set[str]] = {}  # 邻接表，用于快速遍历（下游）
        self.__reverse_adjacency_list: dict[str, set[str]] = {}  # 反向邻接表，用于上游查找
        for node in nodes:
            self.__adjacency_list[node] = set()
            self.__reverse_adjacency_list[node] = set()

    def add_node(self, node: str) -> None:
        """
        添加节点

        Args:
            node: 节点对象

        Raises:
            NodeExistsException: 节点已存在
        """
        if node in self.__nodes:
            raise NodeExistsException(f"节点已存在:{node}")
        self.__nodes.add(node)
        if node not in self.__adjacency_list:
            self.__adjacency_list[node] = set()
        if node not in self.__reverse_adjacency_list:
            self.__reverse_adjacency_list[node] = set()

    def remove_node(self, node: str) -> None:
        """
        删除节点及其相关边

        Args:
            node: 节点对象

        Raises:
            NodeNotFoundException: 节点不存在
        """
        if node not in self.__nodes:
            raise NodeNotFoundException(f"节点不存在:{node}")

        # 删除节点
        self.__nodes.discard(node)

        # 删除与该节点相关的所有边
        edges_to_remove = {(f, t) for f, t in self.__edges if f == node or t == node}
        self.__edges -= edges_to_remove

        # 更新邻接表
        if node in self.__adjacency_list:
            del self.__adjacency_list[node]
        for adjacent in self.__adjacency_list:
            self.__adjacency_list[adjacent].discard(node)

        # 更新反向邻接表
        if node in self.__reverse_adjacency_list:
            del self.__reverse_adjacency_list[node]
        for adjacent in self.__reverse_adjacency_list:
            self.__reverse_adjacency_list[adjacent].discard(node)

    def add_edge(self, _from: str, _to: str) -> None:
        """
        添加边，如果节点不存在则自动添加

        Args:
            _from: 起始节点
            _to: 目标节点

        Raises:
            CycleDetectedException: 如果添加该边会形成环
        """
        # 自动添加不存在的节点
        if _from not in self.__nodes:
            self.add_node(_from)
        if _to not in self.__nodes:
            self.add_node(_to)

        # 检查是否会形成环
        # if self.__would_create_cycle(_from.name, _to.name):
        #     raise CycleDetectedException(f"添加边 {_from} -> {_to} 会形成环")

        # 添加边
        edge = (_from, _to)
        self.__edges.add(edge)
        self.__adjacency_list[_from].add(_to)
        self.__reverse_adjacency_list[_to].add(_from)

    def remove_edge(self, _from: str, _to: str) -> None:
        """
        删除边

        Args:
            _from: 起始节点
            _to: 目标节点

        Raises:
            NodeNotFoundException: 节点不存在
        """
        if _from not in self.__nodes:
            raise NodeNotFoundException(f"节点不存在:{_from}")
        if _to not in self.__nodes:
            raise NodeNotFoundException(f"节点不存在:{_to}")

        # edge = (_from, _to)
        self.__edges.discard((_from, _to))
        if _from in self.__adjacency_list:
            self.__adjacency_list[_from].discard(_to)
        if _to in self.__reverse_adjacency_list:
            self.__reverse_adjacency_list[_to].discard(_from)

    def get_nodes(self) -> list[str]:
        """
        获取所有节点
        Returns:
            节点列表
        """
        return sorted(list(self.__nodes))

    def get_edges(self) -> list[tuple[str, str]]:
        """
        获取所有边（去重）

        Returns:
            边列表，每个元素为 (from, to) 元组
        """
        return sorted(list(self.__edges))

    def __would_create_cycle(self, from_node: str, to_node: str) -> bool:
        """
        检查添加边是否会形成环

        Args:
            from_node: 起始节点
            to_node: 目标节点

        Returns:
            True 如果会形成环
        """
        if from_node == to_node:
            return True

        # 从 to_node 开始DFS，看能否到达 from_node
        visited = set()
        stack = [to_node]

        while stack:
            current = stack.pop()
            if current == from_node:
                return True
            if current not in visited:
                visited.add(current)
                # 获取当前节点的所有下游节点
                if current in self.__adjacency_list:
                    stack.extend(self.__adjacency_list[current])

        return False

    def has_cycle(self) -> bool:
        """
        检测图中是否存在环

        Returns:
            True 如果存在环
        """
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.__adjacency_list.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in self.__nodes:
            if node not in visited:
                if dfs(node):
                    return True

        return False

    def find_downstream(self, node: str) -> "DagGraph":
        """
        查找所有下游依赖的边

        Args:
            node: 起始节点

        Returns:
            下游边的集合
        """
        if node not in self.__nodes:
            return DagGraph()

        from collections import deque

        queue = deque([node])
        visited = set([node])
        all_relations = []

        while queue:
            current = queue.popleft()
            # 使用邻接表直接查找下游节点，提升性能
            neighbors = self.__adjacency_list.get(current, set())
            for neighbor in neighbors:
                edge = (current, neighbor)
                all_relations.append(edge)
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return DagGraph(edges=all_relations)

    def find_upstream(self, node: str) -> "DagGraph":
        """
        查找所有上游依赖的边

        Args:
            node: 目标节点

        Returns:
            上游边的集合
        """
        if node not in self.__nodes:
            return DagGraph()

        from collections import deque

        queue = deque([node])
        visited = set([node])
        all_relations = []

        while queue:
            current = queue.popleft()
            # 使用反向邻接表直接查找上游节点，提升性能
            predecessors = self.__reverse_adjacency_list.get(current, set())
            for predecessor in predecessors:
                edge = (predecessor, current)
                all_relations.append(edge)
                if predecessor not in visited:
                    visited.add(predecessor)
                    queue.append(predecessor)
        return DagGraph(edges=all_relations)

    def to_mermaid(self, direction="LR") -> str:
        """
        转换为 Mermaid 格式字符串

        Returns:
            Mermaid格式的图描述字符串
        """
        mermaid_str = f"graph {direction}"
        for _from, _to in self.__edges:
            mermaid_str += f"\n  {_from} --> {_to}"
        return mermaid_str

    def to_dict(self) -> dict:
        """
        转换为字典格式

        Returns:
            字典格式的图描述
        """
        nodes = [{"id": node, "label": node.split(".")[:-1]} for node in self.__nodes]
        edges = [{"source": _from, "target": _to} for _from, _to in self.__edges]
        return {"nodes": nodes, "edges": edges}

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_html(self) -> str:
        """
        生成包含Mermaid.js可视化的HTML代码

        Args:
            edges: 可选的边集合,如果为None则使用所有边

        Returns:
            包含Mermaid.js可视化的HTML字符串
        """
        # target_edges = edges or self.__edges
        mermaid_content = self.to_mermaid()

        # 读取HTML模板文件
        template_path = Path(__file__).parent.parent / "static" / "mermaid_template.html"

        with open(template_path, encoding="utf-8") as f:
            template = Template(f.read())

        # 替换模板变量
        html_content = template.safe_substitute(title="DAG Visualization", mermaid_content=mermaid_content)

        return html_content
