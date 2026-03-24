
# TODO
- [] 搜索指定表时考虑模糊匹配，当表名不存在时，返回提示或者给出可能的表名（相似度）



## CLI

### output 格式:
- json: 默认格式, 输出 json 格式

1. 搜索命令的输出
```json
{
    "status": "ok",
    "command": "search-table",
    "data": {
        "nodes": [
            {"id": "table1", "label": "ods"},
            {"id": "table2", "label": "dwd"},
        ],
        "edges": [
            {"source": "table1", "target": "table2"}
        ]
    },
    "mermaid": "graph LR\n table1 --> table2",
    "meta": {
        "node_count": 2
    }
}
```


2. 列举命令的输出
```json
{
    "status": "ok",
    "command": "list-tables",
    "tables": [
        "table1",
        "table2"
    ],
    "meta": {
        "table_count": 2
    }
}

```

### CLI 参数
```bash
# 获取所有表名
sqlh list --all --path </path/to/sql-files> --output-format <json|text>

# 获取所有 root 表名
sqlh list --root --path </path/to/sql-files> --output-format <json|text>

# 获取所有 leaf 表名
sqlh list --leaf --path </path/to/sql-files> --output-format <json|text>

# 搜索指定表的root 表名
sqlh search --root --path </path/to/sql-files> --table <table-name> --output-format <json|text>

# 搜索指定表的所有上游表名
sqlh search --upstream --path </path/to/sql-files> --table <table-name> --output-format <json|web|text>

# 搜索指定表的所有下游表名
sqlh search --downstream --path </path/to/sql-files> --table <table-name> --output-format <json|web|text>


# 搜索指定表的所有相关表
sqlh search --all --path </path/to/sql-files> --table <table-name> --output-format <json|web|text>

# 打开全部血缘关系图 web
sqlh web --path </path/to/sql-files>
```