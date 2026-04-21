from sqlh.core.helper import (
    _get_cte_mid_tables,
    get_source_target_tables,
    split_sql,
    split_sql_v2,
    split_sql_v3,
    trim_comment,
)


def test_split():
    """Test SQL splitting functionality."""
    sql = """
    SELECT * FROM t1;
    INSERT INTO t2 SELECT * FROM t1;
    """
    result = split_sql(sql)
    assert len(result) == 2
    assert "SELECT * FROM t1" in result[0]
    assert "INSERT INTO t2 SELECT * FROM t1" in result[1]


def test_split_v2():
    """Test SQL splitting functionality."""
    sql = """/*select '12;', ; */
    -- okk
    SELECT * FROM t1; -- ddd ; 
    INSERT INTO t2 SELECT * FROM t1;
    """
    result = split_sql_v2(sql)
    for stmt in result:
        print("--- SQL Statement ---")
        print(stmt)


def test_split_v3():
    """Test SQL splitting functionality."""
    sql = """/*select '12;', ; */
    -- okk
    SELECT * FROM t1; -- ddd ; 
    INSERT INTO t2 SELECT * FROM t1;
    """
    result = split_sql_v3(sql)
    for stmt in result:
        print("--- SQL Statement ---")
        print(stmt)


def test_trim_comment():
    """Test comment removal."""
    sql = """
    -- This is a comment
    SELECT * FROM t1;
    /* Multi-line
       comment */
    INSERT INTO t2 SELECT * FROM t1;
    """
    result = trim_comment(sql)
    assert "--" not in result
    assert "/*" not in result


def test_get_source_target_tables():
    """Test source/target table extraction."""
    sql = """

"""
    result = get_source_target_tables(sql)
    assert result is not None
    print(result)


def test_get_cte_tables():
    sql = """
with t1 as (
  with t2 as (
    select * from dwd_hive.dwd_hr_youth_p7_normal_income   limit 10 
  )
  select * from t2  
)
, t3 as (
  select * from t1
)
, t4 as (
  select * from t3 
)
select * from t4 
;"""

    result = _get_cte_mid_tables(sql)
    assert result is not None
    assert "t1" in result
    assert "t2" in result
    assert "t3" in result
    assert "t4" in result

    for table in result:
        print(f"CTE Table: {table}")
