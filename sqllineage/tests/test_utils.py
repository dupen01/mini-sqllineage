from sqllineage import utils

# 读取目录或文件 showyu_fastdata_backup_20251202  showyu_llm_backup_20260319
sql_path = "/Users/dunett/codes/duperl/daas-migration/showyu_fastdata_backup_20251202/数字运营三期_数字运营报表"
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


def test_list_command_json():
    s, t, dg = utils.__build_tables_and_graph(sql_stmt_str)
    a = utils.list_command_json(s)
    print(a)


def test_list_command_text():
    s, t, _ = utils.__build_tables_and_graph(sql_stmt_str)
    a = utils.list_command_text(t)
    print(a)


def test_search_command_json():
    _, _, dg = utils.__build_tables_and_graph(sql_stmt_str)
    a = dg.find_upstream("dws.dws_cy_sell_prfmt")

    b = utils.search_command_json(a)
    print(b)
