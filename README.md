




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
sqlh list-tables --all --path </path/to/sql-files> --output-format <json|text>

# 获取所有 root 表名
sqlh list-tables --root --path </path/to/sql-files> --output-format <json|text>

# 获取所有 leaf 表名
sqlh list-tables --leaf --path </path/to/sql-files> --output-format <json|text>

# 搜索指定表的root 表名
sqlh search-table --root --path </path/to/sql-files> --table <table-name> --output-format <json>

# 搜索指定表的所有上游表名
sqlh search-table --upstream --path </path/to/sql-files> --table <table-name> --output-format <json|web>

# 搜索指定表的所有下游表名
sqlh search-table --downstream --path </path/to/sql-files> --table <table-name> --output-format <json|web>

# 搜索指定表的所有相关表
sqlh search-table --all --path </path/to/sql-files> --table <table-name> --output-format <json|web>

# 打开全部血缘关系图 web
sqlh web --path </path/to/sql-files>
```