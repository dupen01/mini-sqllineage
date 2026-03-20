from sqllineage import utils


sql_stmt_str2 = """
-- DWD layer
INSERT INTO dwd_hive.dwd_order
SELECT
    order_id,
    customer_id,
    amount
FROM ods_hive.ods_order;

-- DWS layer
INSERT INTO cc.dws_hive.dws_customer_daily
SELECT
    customer_id,
    COUNT(*) AS order_count,
    SUM(amount) AS total_amount
FROM dwd_hive.dwd_order
GROUP BY customer_id;

-- ADS layer
INSERT INTO ${db}.ads_customer_report
SELECT
    customer_id,
    order_count,
    total_amount
FROM "cc"."dws_hive.dws_customer_daily";
"""


def test_graph():
    dag = utils.__build_tables_and_graph(sql_stmt_str2)[2]
    # print(dag.to_mermaid())
    dg = dag.find_downstream("dwd_hive.dwd_order")
    print(dg.to_mermaid())
    # print(dg.to_json())
    print(dg.get_nodes())
    # print(dag.get_nodes())

