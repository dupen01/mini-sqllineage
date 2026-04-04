"""
SQL parser with token-based analysis.

This module provides SQL parsing functionality using token-based analysis:
|- Splitting multi-statement SQL by semicolons
|- Removing SQL comments (single-line and multi-line)
|- Extracting source and target tables
|- Handling CTE (Common Table Expression) identification

The parser uses keyword-based tokenization rather than full AST parsing,
making it lightweight and fast for simple table/field extraction tasks.
"""

import re

from .keywords import KeyWords


class ParseException(Exception):
    """Exception raised when SQL parsing fails."""

    pass


# ============================================================================
# Module-level functions (replacing SqlHelper class)
# ============================================================================


def split_sql(sql: str) -> list[str]:
    """
    Split multi-statement SQL by semicolons, handling comments and quotes.

    Args:
        sql: SQL statement string

    Returns:
        List of individual SQL statements

    Example:
        >>> split_sql("SELECT 1; SELECT 2;")
        ["SELECT 1", " SELECT 2"]
    """
    result = []
    # 嵌套注释的层级数
    depth = 0
    # 多行SQL的前缀语句,分号之前的语句
    prefix = ""
    sql = sql + ";" if not sql.strip().endswith(";") else sql

    for line in sql.splitlines():
        line = "" if line.strip().startswith("--") else line
        # 标记是否以双引号结尾
        has_terminated_double_quote = True
        # 标记是否以单引号结尾
        has_terminated_single_quote = True
        # 标记是否属于单行注释内容
        is_single_line_comment = False
        # 标记前一个字符是否是短横行 "-"
        was_pre_dash = False
        # 标记前一个字符是否是斜杆 "/"
        was_pre_slash = False
        # 标记前一个字符是否是星号 "*"
        was_pre_star = False
        last_semi_index = 0
        index = 0

        if len(prefix) > 0:
            prefix += "\n"

        for char in line:
            index += 1
            match char:
                case "'":
                    if has_terminated_double_quote:
                        has_terminated_single_quote = not has_terminated_single_quote
                case '"':
                    if has_terminated_single_quote:
                        has_terminated_double_quote = not has_terminated_double_quote
                case "-":
                    if has_terminated_double_quote and has_terminated_single_quote:
                        if was_pre_dash:
                            is_single_line_comment = True
                    was_pre_dash = True
                case "/":
                    if has_terminated_double_quote and has_terminated_single_quote:
                        # 如果'/'前面是'*'， 那么嵌套层级数-1
                        if was_pre_star:
                            depth -= 1
                    was_pre_slash = True
                    was_pre_dash = False
                    was_pre_star = False
                case "*":
                    if has_terminated_double_quote and has_terminated_single_quote:
                        # 如果'*'前面是'/'， 那么嵌套层级数+1
                        if was_pre_slash:
                            depth += 1
                    was_pre_star = True
                    was_pre_dash = False
                    was_pre_slash = False
                case ";":
                    # 当分号不在单引号内，不在双引号内，不属于单行注释，并且多行嵌套注释的层级数为0时，表示此分号应该作为分隔符进行划分
                    if (
                        has_terminated_double_quote
                        and has_terminated_single_quote
                        and not is_single_line_comment
                        and depth == 0
                    ):
                        sql_stmt = prefix + line[last_semi_index : index - 1]
                        result.append(sql_stmt)
                        prefix = ""
                        last_semi_index = index
                case _:
                    was_pre_dash = False
                    was_pre_slash = False
                    was_pre_star = False

        if last_semi_index != index or len(line) == 0:
            prefix += line[last_semi_index:]

    assert depth == 0, f"The number of nested levels of sql multi-line comments is not equal to 0: {depth}"
    if "" in result:
        result.remove("")
    return result


def split_sql_v2(sql: str) -> list[str]:
    """
    Split multi-statement SQL by semicolons, handling comments and quotes.
    Optimized for performance and readability.
    """
    if not sql.strip():
        return []

    result = []
    current_stmt = []

    i = 0
    n = len(sql)

    while i < n:
        char = sql[i]

        # 1. 处理单行注释
        if char == "-" and i + 1 < n and sql[i + 1] == "-":
            # 跳过直到换行符
            while i < n and sql[i] not in ("\n", "\r"):
                i += 1
            if i < n:  # 包含换行符
                current_stmt.append(sql[i])
                i += 1
            continue

        # 2. 处理块注释 /* ... */
        if char == "/" and i + 1 < n and sql[i + 1] == "*":
            current_stmt.append("/*")
            i += 2
            depth = 1
            while i < n and depth > 0:
                if sql[i] == "/" and i + 1 < n and sql[i + 1] == "*":
                    depth += 1
                    current_stmt.append("/*")
                    i += 2
                elif sql[i] == "*" and i + 1 < n and sql[i + 1] == "/":
                    depth -= 1
                    if depth == 0:
                        current_stmt.append("*/")
                        i += 2
                        break
                    current_stmt.append("*/")
                    i += 2
                else:
                    current_stmt.append(sql[i])
                    i += 1
            continue

        # 3. 处理引号
        if char == "'" or char == '"':
            quote_char = char
            current_stmt.append(char)
            i += 1
            while i < n:
                c = sql[i]
                current_stmt.append(c)
                i += 1
                if c == quote_char:
                    # 处理转义引号 '' 或 "" (取决于方言，这里简单处理为成对出现)
                    if i < n and sql[i] == quote_char:
                        current_stmt.append(sql[i])
                        i += 1
                    else:
                        break
            continue

        # 4. 处理分号
        if char == ";":
            stmt_str = "".join(current_stmt)
            if stmt_str.strip():
                result.append(stmt_str)
            current_stmt = []
            i += 1
            continue

        # 5. 普通字符
        current_stmt.append(char)
        i += 1

    # 处理最后剩余的语句
    if current_stmt:
        stmt_str = "".join(current_stmt)
        if stmt_str.strip():
            result.append(stmt_str)

    return result


def _try_parse_dollar_tag(text: str, pos: int) -> tuple[str, int] | None:
    """
    从 text[pos] 开始尝试匹配美元引号开标签 $tag$。
    返回 (tag, end_pos) 或 None。
    """
    # 美元引号标签的合法字符：字母开头，字母/数字/下划线
    _DOLLAR_TAG_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$")

    m = _DOLLAR_TAG_RE.match(text, pos)
    if m:
        tag = m.group(1) or ""
        return tag, m.end()
    return None


def split_sql_v3(text: str) -> list[str]:
    """
    词法解析，完全对应 Rust lib.rs 中的 split_sql()。
    状态：NORMAL / SINGLE_QUOTE / DOUBLE_QUOTE /
          LINE_COMMENT / BLOCK_COMMENT / DOLLAR_QUOTE
    """
    NORMAL = 0
    SINGLE_QUOTE = 1
    DOUBLE_QUOTE = 2
    LINE_COMMENT = 3
    BLOCK_COMMENT = 4
    DOLLAR_QUOTE = 5

    state = NORMAL
    block_depth = 0  # 嵌套块注释深度
    dollar_tag = ""  # 当前美元引号的标签
    dollar_close = ""  # 对应的闭标签字符串（缓存）

    result = []
    stmt_start = 0
    i = 0
    n = len(text)

    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else "\0"

        if state == NORMAL:
            if c == "'":
                state = SINGLE_QUOTE
            elif c == '"':
                state = DOUBLE_QUOTE
            elif c == "-" and nxt == "-":
                state = LINE_COMMENT
                i += 1
            elif c == "/" and nxt == "*":
                state = BLOCK_COMMENT
                block_depth = 1
                i += 1
            elif c == "$":
                parsed = _try_parse_dollar_tag(text, i)
                if parsed is not None:
                    dollar_tag, end = parsed
                    dollar_close = f"${dollar_tag}$"
                    state = DOLLAR_QUOTE
                    i = end
                    continue  # i 已跳过整个开标签，不再 +1
            elif c == ";":
                stmt = text[stmt_start:i].strip()
                if stmt:
                    result.append(stmt)
                stmt_start = i + 1

        elif state == SINGLE_QUOTE:
            if c == "'" and nxt == "'":
                i += 1
            elif c == "\\" and nxt == "'":
                i += 1
            elif c == "'":
                state = NORMAL

        elif state == DOUBLE_QUOTE:
            if c == '"' and nxt == '"':
                i += 1
            elif c == '"':
                state = NORMAL

        elif state == LINE_COMMENT:
            if c == "\n":
                state = NORMAL

        elif state == BLOCK_COMMENT:
            if c == "/" and nxt == "*":
                block_depth += 1
                i += 1
            elif c == "*" and nxt == "/":
                block_depth -= 1
                if block_depth == 0:
                    state = NORMAL
                i += 1

        elif state == DOLLAR_QUOTE:
            if c == "$" and text[i : i + len(dollar_close)] == dollar_close:
                i += len(dollar_close)
                state = NORMAL
                dollar_tag = ""
                dollar_close = ""
                continue

        i += 1

    tail = text[stmt_start:].strip()
    if tail:
        result.append(tail)

    return result


def trim_comment(sql: str) -> str:
    """
    Remove single-line and multi-line comments from SQL.

    Args:
        sql: SQL statement string

    Returns:
        SQL string with comments removed
    """
    # 1. 删除单行注释
    sql = _trim_single_line_comment(sql=sql)

    # 2. 将多行SQL转为单行SQL
    sql = "\\n".join(sql.splitlines())

    # 3. 删除多行注释
    index = 0
    # 嵌套注释的层级数
    depth = 0
    # 标记是否以双引号结尾
    has_terminated_double_quote = True
    # 标记是否以单引号结尾
    has_terminated_single_quote = True
    # 标记前一个字符是否是斜杆 "/"
    was_pre_slash = False
    # 标记前一个字符是否是星号 "*"
    was_pre_star = False
    # 标记是否是SQL Hint
    is_hint = False
    comment_start_index = 0
    comment_end_index = 0
    comment_index_list = []

    for char in sql:
        index += 1
        match char:
            case "'":
                if has_terminated_double_quote:
                    has_terminated_single_quote = not has_terminated_single_quote
            case '"':
                if has_terminated_single_quote:
                    has_terminated_double_quote = not has_terminated_double_quote
            case "/":
                if has_terminated_double_quote and has_terminated_single_quote:
                    # 如果'/'前面是'*'， 那么嵌套层级数-1
                    if was_pre_star:
                        if not is_hint:
                            depth -= 1
                            if depth == 0:
                                comment_end_index = index
                                comment_index_list.append((comment_start_index, comment_end_index))
                        else:
                            is_hint = False
                was_pre_slash = True
                was_pre_star = False
            case "*":
                if has_terminated_double_quote and has_terminated_single_quote:
                    # 如果'*'前面是'/'， 那么嵌套层级数+1
                    if was_pre_slash:
                        depth += 1
                        # 记录层级为1的开始索引
                        if depth == 1:
                            comment_start_index = index - 2
                was_pre_star = True
                was_pre_slash = False
            case "+":
                if has_terminated_double_quote and has_terminated_single_quote:
                    if was_pre_star and depth == 1:
                        is_hint = True
                        depth = 0
                was_pre_star = False
                was_pre_slash = False
            case _:
                was_pre_slash = False
                was_pre_star = False

    for start, end in reversed(comment_index_list):
        sql = sql[:start] + sql[end:]

    # 4. 单行SQL转为多行
    sql = sql.replace("\\n", "\n")
    return sql


def get_source_target_tables(sql: str) -> dict[str, list[str]] | None:
    """
    Extract source and target tables from a single SQL statement.

    This method uses token-based parsing to identify table dependencies.
    CTE (Common Table Expression) intermediate tables are filtered out.

    Args:
        sql: Single SQL statement string

    Returns:
        Dictionary with keys:
            - "source_tables": list of source table names
            - "target_tables": list of target table names
        Returns None if no tables found

    Raises:
        ParseException: If SQL contains multiple statements

    Note:
        TODO: 不能识别join后面的 [hint] table_name, 需要优化
        {
            "source_tables": [(t1, 1), (t2, 2), (t3, 3)],
            "target_tables": [(t4, 1)]
        }
    """
    # 预处理：去掉多行注释和单行注释
    sql = trim_comment(sql).strip()
    # 删除末尾的`;`
    sql = sql[:-1] if sql.endswith(";") else sql

    # 校验SQL参数
    if len(split_sql(sql)) > 1:
        raise ParseException("sql脚本为多条SQL语句,需传入单条SQL语句.")

    was_pre_insert = False
    was_pre_from = False
    was_pre_as = False
    was_merge = False
    was_using = False
    was_pre_table_name = False
    was_pre_table_function = False
    target_tables: list[str] = []
    source_tables: list[str] = []
    result: dict[str, list[str]] = {}

    for line in sql.splitlines():
        line = line.strip()
        if len(line) == 0:
            continue

        line = line.replace("(", " ( ")
        line = line.replace(")", " ) ")
        line = line.replace(",", " , ")

        for token in line.split(" "):
            token = token.strip()
            if len(token) == 0:
                continue

            if token.upper() == "AS":
                was_pre_as = True
                continue

            if token.upper() in KeyWords.insert_keywords:
                was_pre_insert = True
                was_pre_from = False
                continue

            if token.upper() == "MERGE":
                was_merge = True
                continue

            if token.upper() == "USING":
                was_using = True
                continue

            if token.upper() in KeyWords.from_keywords:
                was_pre_from = True
                was_pre_insert = False
                was_pre_table_name = False
                continue

            if was_pre_as and token.upper() not in KeyWords.keywords:
                was_pre_as = False
                was_pre_table_name = False
                continue

            if token.upper() in KeyWords.keywords:
                if was_pre_insert or was_pre_from:
                    was_pre_from = False
                continue

            if token.upper() not in KeyWords.keywords and was_pre_insert:
                target_tables.append(token)
                was_pre_insert = False
                was_pre_from = False
                continue

            if token.upper() in KeyWords.table_function_keywords and was_pre_from:
                was_pre_table_function = True
                continue

            # merge into
            if was_merge and not was_using and token.upper() not in KeyWords.keywords and len(target_tables) == 0:
                target_tables.append(token)
                continue

            if was_merge and was_using and token.upper() not in KeyWords.keywords:
                if token != "(":
                    source_tables.append(token)
                was_using = False
                was_merge = False
                continue

            if was_pre_from:
                if (
                    token not in KeyWords.keywords
                    and not was_pre_table_name
                    and token not in (",", "(")
                    and not was_pre_table_function
                ):
                    source_tables.append(token)
                    was_pre_from = True
                    was_pre_table_name = True
                if token in ["AS", ","]:
                    was_pre_from = True
                    was_pre_table_name = False

    mid_table = _get_cte_mid_tables(sql)
    source_tables = list(set(source_tables) - set(mid_table))
    if len(source_tables) != 0:
        result.setdefault("target_tables", target_tables)
        result.setdefault("source_tables", source_tables)
        return result
    else:
        return


def get_source_target_tables_v2(sql: str) -> dict[str, list[str]] | None:
    """
    Extract source and target tables from a single SQL statement using a token-based approach.
    """
    # 1. 预处理
    clean_sql = trim_comment(sql).strip()
    if not clean_sql:
        return None

    # 去除末尾分号
    if clean_sql.endswith(";"):
        clean_sql = clean_sql[:-1]

    # 校验多语句
    # 注意：这里直接传原始 sql 给 split_sql 可能更稳妥，或者传 clean_sql 取决于 split_sql 的实现
    if len(split_sql(clean_sql)) > 1:
        raise ParseException("sql脚本为多条SQL语句,需传入单条SQL语句.")

    # 2. 分词 (使用正则优化性能)
    # 匹配单词、括号、逗号。忽略空白字符。
    # tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[()]|,", clean_sql)
    tokens = re.findall(r"\[[^\]]+\]|[A-Za-z_][A-Za-z0-9_]*|[()]|,", clean_sql)

    if not tokens:
        return None

    # 3. 状态机变量
    source_tables = set()
    target_tables = set()

    # 状态标志
    # 状态标志
    is_insert_context = False
    is_from_context = False
    is_join_context = False  # 新增：专门标记 JOIN 后的状态
    is_using_context = False
    is_merge_context = False

    # 辅助变量

    for token in tokens:
        token_upper = token.upper()

        # --- 特殊处理：跳过 Hint 内容 ---
        # 如果 token 是 [...] 格式，直接跳过，不要把它当成括号或关键字
        if token.startswith("[") and token.endswith("]"):
            # 如果是在 JOIN 后面遇到的 Hint，保持 join_context 为 True
            # 如果是在 FROM 后面遇到的 Hint，保持 from_context 为 True
            continue

        # --- 上下文重置 ---
        if token == "(":
            # 左括号通常意味着子查询，重置 FROM/JOIN 上下文
            # 但我们不能重置 INSERT 上下文
            is_from_context = False
            is_join_context = False
            is_using_context = False
            continue

        # --- 关键字状态流转 ---

        if token_upper in KeyWords.insert_keywords:
            is_insert_context = True
            is_from_context = False
            is_join_context = False
            continue

        if token_upper == "FROM":
            is_from_context = True
            is_join_context = False
            is_insert_context = False
            continue

        # 修复核心：处理 JOIN
        if token_upper in ["JOIN", "INNER", "LEFT", "RIGHT", "OUTER", "CROSS"]:
            is_from_context = True  # JOIN 也是一种来源
            is_join_context = True  # 标记刚刚遇到了 JOIN，下一个非关键字即为表名
            continue

        # 【关键修复】：遇到 ON，说明表名部分结束了，后面是关联条件
        if token_upper == "ON":
            is_from_context = False
            is_join_context = False
            continue

        if token_upper == "MERGE":
            is_merge_context = True
            continue

        if token_upper == "USING":
            is_from_context = False
            is_join_context = False
            if is_merge_context:
                is_using_context = True
            continue

        # --- 表名捕获逻辑 ---

        # 1. INSERT 目标表
        if is_insert_context and token_upper not in KeyWords.keywords and token not in ("(", ")"):
            target_tables.add(token)
            is_insert_context = False
            continue

        # 2. MERGE 逻辑 (略，保持原有逻辑) ...
        if is_merge_context and not is_using_context and token_upper not in KeyWords.keywords:
            target_tables.add(token)
            is_merge_context = False
            continue

        if is_using_context and token_upper not in KeyWords.keywords:
            if token != "(":
                source_tables.add(token)
            is_using_context = False
            is_merge_context = False
            continue

        # 3. FROM / JOIN 源表 (修复核心)
        # 条件：处于 FROM 或 JOIN 状态，且不是关键字，且不是括号/逗号
        if (is_from_context or is_join_context) and token_upper not in KeyWords.keywords and token not in ("(", ")", ","):
            source_tables.add(token)

            # 捕获到表名后，重置状态，等待下一个 JOIN 或逗号
            is_join_context = False
            # 注意：is_from_context 保持 True，以便处理 "FROM t1, t2" 这种逗号分隔的情况
            continue

        # 处理逗号：逗号意味着可能有下一个表名，重置别名状态，保持 FROM 上下文
        if token == ",":
            is_join_context = False
            # is_from_context 保持不变
            continue

    # 4. 过滤 CTE 中间表
    # 注意：_get_cte_mid_tables 需要解析 WITH 子句，这里假设它工作正常
    cte_tables = _get_cte_mid_tables(clean_sql)
    source_tables -= set(cte_tables)

    # 5. 构建结果
    if source_tables or target_tables:
        return {"source_tables": list(source_tables), "target_tables": list(target_tables)}

    return None


# ============================================================================
# Private helper functions
# ============================================================================


def _trim_single_line_comment(sql: str) -> str:
    """删除单行注释"""
    result = []
    for line in sql.splitlines():
        line = line.strip()
        line = "" if line.startswith("--") else line
        line = "" if line.startswith("#") else line
        if len(line) == 0:
            continue

        # 标记是否以双引号结尾
        has_terminated_double_quote = True
        # 标记是否以单引号结尾
        has_terminated_single_quote = True
        # 标记前一个字符是否是短横行 "-"
        was_pre_dash = False
        index = 0

        for char in line:
            index += 1
            match char:
                case "'":
                    if has_terminated_double_quote:
                        has_terminated_single_quote = not has_terminated_single_quote
                case '"':
                    if has_terminated_single_quote:
                        has_terminated_double_quote = not has_terminated_double_quote
                case "-":
                    if has_terminated_double_quote and has_terminated_single_quote:
                        if was_pre_dash:
                            line = line[: index - 2]
                            continue
                    was_pre_dash = True
                case "#":
                    if has_terminated_double_quote and has_terminated_single_quote:
                        line = line[: index - 1]
                        continue
                case _:
                    was_pre_dash = False

        result.append(line)
    return "\n".join(result)


def _get_cte_mid_tables(sql: str) -> list:
    """获取cte语句的临时表名"""
    # 括号层级
    bracket_level = 0
    was_pre_with = False
    is_cte = False
    was_pre_right_bracket = False
    result = []

    # 预处理：去掉多行注释和单行注释
    sql = trim_comment(sql)

    for line in sql.splitlines():
        line = line.strip()
        if len(line) == 0:
            continue

        line = line.replace("(", " ( ")
        line = line.replace(")", " ) ")
        line = line.replace(",", " , ")

        for token in line.split(" "):
            token = token.strip()
            if len(token) == 0:
                continue

            if token.upper() == "(":
                bracket_level += 1
            if token.upper() == ")":
                bracket_level -= 1
                was_pre_right_bracket = True
            if token.upper() == "WITH":
                was_pre_with = True
                is_cte = True
                continue

            if token.upper() in KeyWords.keywords:
                if was_pre_right_bracket and is_cte and bracket_level == 0 and token.upper() != "AS":
                    is_cte = False

            if token.upper() not in KeyWords.keywords:
                if was_pre_with:
                    result.append(token)
                if is_cte and bracket_level == 0 and not was_pre_with and token not in (",", "(", ")"):
                    result.append(token)
                was_pre_with = False

    return result
