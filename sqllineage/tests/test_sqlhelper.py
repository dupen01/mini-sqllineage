from sqllineage.core.helper import get_source_target_tables, split_sql, trim_comment


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
