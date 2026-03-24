from typing import Tuple

from sqllineage import utils

# 读取目录或文件 showyu_fastdata_backup_20251202  showyu_llm_backup_20260319
sql_path = "/Users/dunett/codes/duperl/daas-migration/showyu_llm_backup_20260319"
sql_stmt_str = utils.read_sql_from_directory(sql_path)


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
    a = utils.search_related_upstream_tables(sql_stmt_str, "dws.dws_cy_cust_ltst_active_rec")
    if isinstance(a, Tuple):
        print(utils.list_command_text(a[0]))
    else:
        print(a)


def test_search_related_downstream_tables():
    a = utils.search_related_downstream_tables(sql_stmt_str, "ods.ods_plr_dwm_hr_xy_shop_performance_all")
    if isinstance(a, Tuple):
        print(utils.list_command_text(a[0]))
    else:
        print(a)


def test_search_related_tables():
    a = utils.search_related_tables(sql_stmt_str, "dim.dim_shopinfo")
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
    output = utils.search_related_root_tables(sql_stmt_str, "ods_hive.ods_ec_staff22")
    # print(utils.list_command_text(output[0]))
    if isinstance(output, Tuple):
        print(utils.list_command_text(output[0]))
    else:
        print(output)
