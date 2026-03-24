import argparse
from pathlib import Path

from sqlh import __version__

from .utils import (
    get_all_dag,
    get_all_leaf_tables,
    get_all_root_tables,
    get_all_tables,
    list_command_json,
    list_command_text,
    read_sql_from_directory,
    search_command_json,
    search_command_text,
    search_related_downstream_tables,
    search_related_root_tables,
    search_related_tables,
    search_related_upstream_tables,
    visualize_dag,
)


def _create_parent_parser():
    """创建包含共享参数的父解析器"""
    parent_parser = argparse.ArgumentParser(add_help=False)

    # 共享参数: 所有子命令都支持 -s/--sql 或 -p/--path
    sql_or_path = parent_parser.add_mutually_exclusive_group(required=True)
    sql_or_path.add_argument("-s", "--sql", dest="sql", help="sql statement")
    sql_or_path.add_argument("-p", "--path", dest="path", help="sql file or directory path")

    # 共享参数: 所有子命令都支持输出格式
    parent_parser.add_argument(
        "-f",
        "--output-format",
        choices=["json", "text", "web", "html"],
        default="json",
        help="output format",
    )

    return parent_parser


def arg_parse():
    parser = argparse.ArgumentParser(usage="%(prog)s [OPTIONS] <COMMAND>", description="mini-sqllineage")
    parser.add_argument("-v", "--version", action="version", version=__version__)

    # 获取共享参数的父解析器
    parent_parser = _create_parent_parser()

    # 子命令
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list-tables 子命令
    list_parser = subparsers.add_parser(
        "list",
        parents=[parent_parser],
        help="list all tables / root tables / leaf tables",
        add_help=False,
    )
    list_target = list_parser.add_mutually_exclusive_group(required=True)
    list_target.add_argument("--all", action="store_true", help="list all tables")
    list_target.add_argument("--root", action="store_true", help="list root tables (tables with no dependencies)")
    list_target.add_argument("--leaf", action="store_true", help="list leaf tables (tables not used by others)")
    list_parser.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help="show this help message")

    # search-table 子命令
    search_parser = subparsers.add_parser(
        "search",
        parents=[parent_parser],
        help="search table relationships",
        add_help=False,
    )
    search_direction = search_parser.add_mutually_exclusive_group(required=True)
    search_direction.add_argument("--root", action="store_true", help="search root tables of the specified table")
    search_direction.add_argument("--upstream", action="store_true", help="search upstream tables (dependencies)")
    search_direction.add_argument("--downstream", action="store_true", help="search downstream tables (dependents)")
    search_direction.add_argument("--all", action="store_true", help="search both upstream and downstream tables")
    search_parser.add_argument("-t", "--table", help="table name to search", required=True)
    search_parser.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help="show this help message")

    # web 子命令
    web_parser = subparsers.add_parser(
        "web",
        parents=[parent_parser],
        help="start web server for visualization",
        add_help=False,
    )
    web_parser.add_argument("--html-path", help="html file path for visualization", default=".")
    web_parser.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help="show this help message")

    return parser.parse_args()


def main():
    args = arg_parse()

    if args.sql:
        sql_stmt_str = args.sql
    else:
        sql_stmt_str = read_sql_from_directory(args.path)

    if args.command == "list":
        if args.all:
            output = get_all_tables(sql_stmt_str)
            sub_command_arg = "--all"
        elif args.root:
            output = get_all_root_tables(sql_stmt_str)
            sub_command_arg = "--root"
        elif args.leaf:
            output = get_all_leaf_tables(sql_stmt_str)
            sub_command_arg = "--leaf"

        if args.output_format == "json":
            print(list_command_json(output, sub_command_arg))
        else:
            print(list_command_text(output))

    elif args.command == "search":
        if args.root:
            output = search_related_root_tables(sql_stmt_str, args.table)
            sub_command_arg = "--root"
        elif args.upstream:
            output = search_related_upstream_tables(sql_stmt_str, args.table)
            sub_command_arg = "--upstream"
        elif args.downstream:
            output = search_related_downstream_tables(sql_stmt_str, args.table)
            sub_command_arg = "--downstream"
        elif args.all:
            output = search_related_tables(sql_stmt_str, args.table)
            sub_command_arg = "--all"

        if args.output_format == "json":
            print(search_command_json(output, sub_command_arg))
        elif args.output_format in ["web", "html"]:
            if isinstance(output, tuple):
                visualize_dag(output[1], template_type="mermaid", filename="lineage_mermaid.html")
            else:
                print(output)
        elif args.output_format == "text":
            print(search_command_text(output))

    elif args.command == "web":
        html_file_path = Path(args.html_path) / "lineage_dagre.html"
        print(f"open web page: {html_file_path}")
        visualize_dag(get_all_dag(sql_stmt_str), template_type="dagre", filename=html_file_path)
        return
