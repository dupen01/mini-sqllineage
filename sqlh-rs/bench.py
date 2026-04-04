#!/usr/bin/env python3
"""
基准测试脚本：生成测试数据，分别跑 Python 和 Rust，对比结果
用法: python3 bench.py
"""

import os
import random
import string
import subprocess
import sys
import tempfile
import time

# ── 生成测试 SQL 数据 ─────────────────────────────────────────────────────────

TEMPLATES = [
    "SELECT {cols} FROM {table} WHERE {col} = '{val}';",
    "INSERT INTO {table} ({cols}) VALUES ('{val}', {num});",
    "UPDATE {table} SET {col} = '{val}' WHERE id = {num};",
    "DELETE FROM {table} WHERE {col} = {num};",
    "CREATE INDEX idx_{col} ON {table}({col});",
    "-- comment: update batch {num}\nUPDATE {table} SET {col} = {num};",
    "SELECT {col} FROM {table}; /* inline comment; with semicolon */",
    "INSERT INTO {table} VALUES('tricky;value;here', {num});",
]


def rand_str(n=6):
    return "".join(random.choices(string.ascii_lowercase, k=n))


def gen_sql_file(num_statements: int) -> str:
    lines = []
    for _ in range(num_statements):
        tpl = random.choice(TEMPLATES)
        stmt = tpl.format(
            table=rand_str(),
            col=rand_str(),
            cols=f"{rand_str()}, {rand_str()}",
            val=rand_str(12),
            num=random.randint(1, 99999),
        )
        lines.append(stmt)
    return "\n".join(lines)


# ── 运行测试 ─────────────────────────────────────────────────────────────────


def run_python(sql_dir: str, runs: int = 5) -> float:
    """返回平均解析耗时（ms）"""
    # 直接在进程内运行，避免进程启动开销影响计时
    sys.path.insert(0, os.path.dirname(__file__))
    from sql_splitter import read_sql_dir, split_sql

    times = []
    for _ in range(runs):
        combined, _ = read_sql_dir(sql_dir)
        t = time.perf_counter()
        result = split_sql(combined)
        times.append((time.perf_counter() - t) * 1000)

    avg = sum(times) / len(times)
    stmt_count = len(result)
    size_mb = len(combined.encode()) / 1024 / 1024
    return avg, stmt_count, size_mb


def run_rust(sql_dir: str, binary: str) -> float | None:
    """调用编译好的 Rust 二进制，返回其报告的解析耗时（ms）"""
    if not os.path.exists(binary):
        return None
    try:
        out = subprocess.check_output(
            [binary, sql_dir, "--bench"],
            text=True,
        )
        for line in out.splitlines():
            if "解析耗时" in line:
                # 格式: "解析耗时  : 1.234 ms"
                return float(line.split(":")[1].strip().split()[0])
    except Exception as e:
        print(f"Rust 运行失败: {e}")
    return None


# ── 主流程 ────────────────────────────────────────────────────────────────────


def main():
    sizes = [
        ("小型 (1k 条语句)", 1_000),
        ("中型 (50k 条语句)", 50_000),
        ("大型 (200k 条语句)", 200_000),
    ]

    # 查找 Rust 二进制
    rust_bin = os.path.join(os.path.dirname(__file__), "target", "release", "sql_splitter")
    has_rust = os.path.exists(rust_bin)
    if not has_rust:
        print("⚠️  未找到 Rust 二进制，只跑 Python。")
        print("   编译方法: cargo build --release")
        print()

    print(f"{'场景':<22} {'数据量':>8}  {'Python 解析':>12}  {'Rust 解析':>12}  {'加速比':>8}")
    print("─" * 72)

    for label, n_stmts in sizes:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 生成 4 个 sql 文件
            for fi in range(4):
                content = gen_sql_file(n_stmts // 4)
                with open(os.path.join(tmpdir, f"test_{fi:02d}.sql"), "w") as f:
                    f.write(content)

            py_ms, stmt_count, size_mb = run_python(tmpdir, runs=3)
            py_str = f"{py_ms:.2f} ms"

            if has_rust:
                rs_ms = run_rust(tmpdir, rust_bin)
                rs_str = f"{rs_ms:.2f} ms" if rs_ms else "N/A"
                ratio = f"{py_ms / rs_ms:.1f}x" if rs_ms else "N/A"
            else:
                rs_str = "未编译"
                ratio = "—"

            print(f"{label:<22} {size_mb:>6.1f}MB  {py_str:>12}  {rs_str:>12}  {ratio:>8}")

    print()
    if not has_rust:
        print("编译 Rust 后重新运行此脚本即可看到对比数据。")
        print("预期：相同逻辑下 Rust 解析速度约为 Python 的 20–60 倍。")


if __name__ == "__main__":
    main()
