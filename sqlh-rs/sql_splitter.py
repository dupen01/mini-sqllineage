"""
Python 等效实现 —— 用于与 Rust 版本做基准对比
支持：单引号、双引号、行注释、块注释（嵌套）、美元引号 $$ / $tag$
用法: python3 sql_splitter.py <sql目录> [--bench]
"""

import re
import sys
import time
from pathlib import Path

# 美元引号标签的合法字符：字母开头，字母/数字/下划线
_DOLLAR_TAG_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$")


def _try_parse_dollar_tag(text: str, pos: int) -> tuple[str, int] | None:
    """
    从 text[pos] 开始尝试匹配美元引号开标签 $tag$。
    返回 (tag, end_pos) 或 None。
    """
    m = _DOLLAR_TAG_RE.match(text, pos)
    if m:
        tag = m.group(1) or ""
        return tag, m.end()
    return None


def split_sql(text: str) -> list[str]:
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


def read_sql_dir(directory: str) -> tuple[str, int]:
    dir_path = Path(directory)
    files = sorted(dir_path.rglob("*.sql"))  # 递归查找所有 .sql 文件
    parts = []
    for file_path in files:
        parts.append(file_path.read_text(encoding="utf-8"))
        parts.append("\n")

    return "".join(parts), len(files)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 sql_splitter.py <sql目录> [--bench]", file=sys.stderr)
        sys.exit(1)

    directory = sys.argv[1]
    bench_mode = len(sys.argv) > 2 and sys.argv[2] == "--bench"

    t0 = time.perf_counter()
    combined, file_count = read_sql_dir(directory)
    t_read = time.perf_counter() - t0

    t1 = time.perf_counter()
    statements = split_sql(combined)
    t_parse = time.perf_counter() - t1

    t_total = time.perf_counter() - t0

    if bench_mode:
        size_mb = len(combined.encode()) / 1024 / 1024
        parse_speed = size_mb / t_parse if t_parse > 0 else float("inf")
        print("=== 性能统计 ===")
        print(f"文件数量  : {file_count} 个")
        print(f"总字符数  : {len(combined.encode())} 字节 ({size_mb:.2f} MB)")
        print(f"SQL 语句数 : {len(statements)} 条")
        print(f"读取耗时  : {t_read * 1000:.3f} ms")
        print(f"解析耗时  : {t_parse * 1000:.3f} ms")
        print(f"总耗时    : {t_total * 1000:.3f} ms")
        print(f"解析速度  : {parse_speed:.1f} MB/s")
    else:
        print(f"读取了 {file_count} 个文件，共 {len(statements)} 条 SQL：")
        for i, stmt in enumerate(statements, 1):
            print(f"── [{i}] ──────────────────")
            preview = stmt[:120]
            print(preview + ("..." if len(stmt) > 120 else ""))


if __name__ == "__main__":
    main()
