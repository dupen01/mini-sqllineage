from sqllineage import utils

# 读取目录或文件
sql_path = "/Users/dunett/codes/duperl/daas-migration/showyu_llm_backup_20260319"
sql_stmt_str = utils.read_sql_from_directory(sql_path)


def test_get_all_tables():
    a = utils.get_all_tables(sql_stmt_str)
    for i in a:
        print(i)


def test_get_all_root_tables():
    a = utils.get_all_root_tables(sql_stmt_str)
    for i in a:
        print(i)


def test_search_related_root_tables():
    a = utils.search_related_root_tables(sql_stmt_str, "dws.dws_cy_sell_prfmt")
    if a is None:
        print("None")
    else:
        for i in a:
            print(i)


def test_search_related_upstream_tables():
    a = utils.search_related_upstream_tables(sql_stmt_str, "dws.dws_cy_sell_prfmt")
    if a is None:
        print("None")
    else:
        for i in a:
            print(i)


def test_search_related_tables():
    a = utils.search_related_tables(sql_stmt_str, "dim.dim_shopinfo")
    if a is None:
        print("None")
    else:
        for i in a:
            print(i)


def test_get_all_leaf_tables():
    a = utils.get_all_leaf_tables(sql_stmt_str)
    for i in a:
        print(i)


def test_visualize_graph():
    dag = utils.__build_tables_and_graph(sql_stmt_str)[2]
    utils.__visualize_dag(dag)
