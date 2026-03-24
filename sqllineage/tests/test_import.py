from sqllineage import DagGraph
from sqllineage import get_all_tables
from sqllineage import split_sql


def test_daggraph():
    dag = DagGraph()
    print(dag.get_nodes())


def test_get_all_tables():
    sql_stmt_str = "select * from dim.dim_shopinfo"
    print(get_all_tables(sql_stmt_str))

def test_split_sql():
    sql_stmt_str = "select * from dim.dim_shopinfo; select 123"
    print(split_sql(sql_stmt_str))
