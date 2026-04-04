from sqlh.core.helper import (
    get_source_target_tables,
    get_source_target_tables_v2,
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
    sql = "INSERT INTO dwd.user_dim SELECT * FROM ods.user;"
    result = get_source_target_tables(sql)
    assert result is not None
    assert "ods.user" in result["source_tables"]
    assert "dwd.user_dim" in result["target_tables"]


def test_get_source_target_tables_v2():
    """Test source/target table extraction."""
    sql = "SELECT COUNT(*) FROM t2 JOIN [broadcast] t1 ON t1.c1 = t2.c2;"
    result = get_source_target_tables_v2(sql)
    for table in result["source_tables"]:
        print(f"Source Table: {table}")
