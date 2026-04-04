# SQL Splitter — Rust vs Python 性能对比

读取目录下所有 `.sql` 文件，拼接后进行词法解析，按分号分割为 SQL 语句列表。

## 支持的语法（PostgreSQL 方言）

| 场景 | 举例 | 处理方式 |
|------|------|----------|
| 普通分号 | `SELECT 1; SELECT 2` | 正常分割 |
| 单引号字符串内的分号 | `'val;ue'` | 忽略，不分割 |
| 双引号标识符内的分号 | `"col;name"` | 忽略，不分割 |
| 单行注释内的分号 | `-- comment; here` | 忽略，不分割 |
| 多行注释内的分号 | `/* comment; */` | 忽略，不分割 |
| **嵌套块注释** | `/* outer /* inner; */ */` | 正确计数深度 |
| **美元引号（匿名）** | `$$ body; $$` | 忽略，不分割 |
| **美元引号（标签）** | `$body$ body; $body$` | 忽略，不分割 |
| **美元引号嵌套** | `$outer$ … $$ … $$ … $outer$` | 不同标签可嵌套 |
| **参数占位符** | `$1, $2` | 不会误识别为美元引号 |
| 连续分号 | `SELECT 1;;;` | 空语句过滤掉 |
| 转义单引号 | `'it''s'` 或 `'it\'s'` | 正确处理 |

## 项目结构

```
sqlh-rs/
├── Cargo.toml          # Rust 项目配置
├── src/
│   ├── lib.rs          # 核心词法解析逻辑（可被其他 Rust 代码引用）
│   └── main.rs         # CLI 入口
├── sql_splitter.py     # Python 等效实现（逻辑完全对应 lib.rs）
└── bench.py            # 基准测试：自动生成数据，对比 Python vs Rust
```

## 快速开始

### 编译 Rust

```bash
cd sqlh-rs
cargo build --release
# 二进制位于 target/release/sql_splitter
```

### 运行 Rust CLI

```bash
# 普通模式：打印解析结果
./target/release/sql_splitter /path/to/sql/dir

# 性能模式：打印耗时统计
./target/release/sql_splitter /path/to/sql/dir --bench
```

输出示例：
```
=== 性能统计 ===
文件数量  : 12 个
总字符数  : 8523144 字节 (8.13 MB)
SQL 语句数 : 52847 条
读取耗时  : 12.341 ms
解析耗时  : 3.872 ms        ← 纯词法解析时间
总耗时    : 16.213 ms
解析速度  : 2099.8 MB/s
```

### 运行 Python 版本

```bash
python3 sql_splitter.py /path/to/sql/dir --bench
```

### 运行基准对比

```bash
# 先编译 Rust，再运行对比脚本
cargo build --release
python3 bench.py
```

输出示例：
```
场景                     数据量   Python 解析    Rust 解析    加速比
────────────────────────────────────────────────────────────────────────
小型 (1k 条语句)          0.1MB      2.14 ms       0.04 ms     53.5x
中型 (50k 条语句)         4.8MB     98.32 ms       2.11 ms     46.6x
大型 (200k 条语句)       19.2MB    401.77 ms       8.43 ms     47.6x
```

## 单元测试

```bash
cargo test
```

## 作为库引用（Rust）

```rust
use sql_splitter::{read_sql_dir, split_sql};
use std::path::Path;

fn main() {
    let (combined, _) = read_sql_dir(Path::new("./sqls")).unwrap();
    let stmts = split_sql(&combined);
    println!("共 {} 条 SQL", stmts.len());
}
```

## 关键设计说明

### 零拷贝设计
`split_sql` 返回 `Vec<&str>`，所有切片都指向原始字符串，
不做任何内存拷贝。对于大文件场景内存效率极高。

### 字节级遍历
内部使用 `input.as_bytes()` 做字节遍历而非字符遍历，
因为 SQL 关键字符（`;` `'` `"` `-` `/` `*`）均是 ASCII，
字节操作比 Unicode char 迭代更快。

### 状态机
5 个状态的有限状态机，单次遍历完成，时间复杂度 O(n)。