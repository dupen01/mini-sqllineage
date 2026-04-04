from typing import Tuple

from sqlh import utils

# 读取目录或文件
sql_path = ""
sql_stmt_str = utils.read_sql_from_directory(sql_path)
sql_stmt_str = """insert into t3 SELECT /*+edede */ COUNT(*) FROM t2 JOIN [broadcast] t1 ON t1.c1 = t2.c2;"""

def test_read_sql_from_directory():
    import timeit

    print(timeit.timeit(lambda: utils.read_sql_from_directory(sql_path), number=100))


def test_get_all_tables():
    a = utils.get_all_tables(sql_stmt_str)
    for i in a:
        print(i)


def test_get_all_root_tables():
    a = utils.get_all_root_tables(sql_stmt_str)
    for i in a:
        print(i)


def test_search_related_upstream_tables():
    a = utils.search_related_upstream_tables(sql_stmt_str, "dws.xxx")
    if isinstance(a, Tuple):
        print(utils.list_command_text(a[0]))
    else:
        print(a)


def test_search_related_downstream_tables():
    a = utils.search_related_downstream_tables(sql_stmt_str, "ods_hive.ods_order")
    if isinstance(a, Tuple):
        print(utils.list_command_text(a[0]))
    else:
        print(a)


def test_search_related_tables():
    a = utils.search_related_tables(sql_stmt_str, "ods_hive.ods_order")
    if isinstance(a, Tuple):
        print(utils.list_command_text(a[0]))
    else:
        print(a)


def test_get_all_leaf_tables():
    a = utils.get_all_leaf_tables(sql_stmt_str)
    for i in a:
        print(i)


def test_visualize_graph():
    dag = utils.__build_tables_and_graph(sql_stmt_str)[2]
    utils.visualize_dag(dag)


def test_list_command_json():
    s, t, dg = utils.__build_tables_and_graph(sql_stmt_str)
    a = utils.list_command_json(s, "xxx")
    print(a)


def test_list_command_text():
    s, t, _ = utils.__build_tables_and_graph(sql_stmt_str)
    a = utils.list_command_text(t)
    print(a)


def test_search_command_json():
    _, _, dg = utils.__build_tables_and_graph(sql_stmt_str)
    ...


def test_search_related_root_tables():
    output = utils.search_related_root_tables(sql_stmt_str, "ods_hive.ods_order")
    # print(utils.list_command_text(output[0]))
    if isinstance(output, Tuple):
        print(utils.list_command_text(output[0]))
    else:
        print(output)


def test_table_count():
    print(utils.table_count(sql_stmt_str))
    for table, count in utils.table_count(sql_stmt_str, "ods_hive.ods_order"):
        print(f"{table}: {count}")
