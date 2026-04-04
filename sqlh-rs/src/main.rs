use sql_splitter::{read_sql_dir, split_sql};
use std::env;
use std::path::Path;
use std::time::Instant;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        eprintln!("用法: sql_splitter <sql目录路径> [--bench]");
        eprintln!("  --bench  输出耗时统计而不是 SQL 列表");
        std::process::exit(1);
    }

    let dir = Path::new(&args[1]);
    let bench_mode = args.get(2).map(|s| s == "--bench").unwrap_or(false);

    // ── 1. 读取文件 ──────────────────────────────
    let t0 = Instant::now();

    let (combined, file_count) = match read_sql_dir(dir) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("读取目录失败: {e}");
            std::process::exit(1);
        }
    };

    let t_read = t0.elapsed();

    // ── 2. 词法解析 ──────────────────────────────
    let t1 = Instant::now();
    let statements = split_sql(&combined);
    let t_parse = t1.elapsed();

    let t_total = t0.elapsed();

    // ── 3. 输出 ──────────────────────────────────
    if bench_mode {
        println!("=== 性能统计 ===");
        println!("文件数量  : {} 个", file_count);
        println!("总字符数  : {} 字节 ({:.2} MB)", combined.len(), combined.len() as f64 / 1024.0 / 1024.0);
        println!("SQL 语句数 : {} 条", statements.len());
        println!("读取耗时  : {:.3} ms", t_read.as_secs_f64() * 1000.0);
        println!("解析耗时  : {:.3} ms", t_parse.as_secs_f64() * 1000.0);
        println!("总耗时    : {:.3} ms", t_total.as_secs_f64() * 1000.0);
        println!(
            "解析速度  : {:.1} MB/s",
            combined.len() as f64 / 1024.0 / 1024.0 / t_parse.as_secs_f64()
        );
    } else {
        println!("读取了 {} 个文件，共 {} 条 SQL：", file_count, statements.len());
        for (i, stmt) in statements.iter().enumerate() {
            println!("── [{}] ──────────────────", i + 1);
            // 输出前 120 字符预览
            let preview: String = stmt.chars().take(120).collect();
            if stmt.len() > 120 {
                println!("{}...", preview);
            } else {
                println!("{}", preview);
            }
        }
    }
}
