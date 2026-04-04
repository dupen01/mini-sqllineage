/// SQL 词法分割器
///
/// 支持：
///   - 单引号字符串内的分号忽略：  'val;ue'
///   - 双引号标识符内的分号忽略：  "col;name"
///   - 单行注释内的分号忽略：      -- comment;
///   - 多行注释内的分号忽略：      /* comment; */
///   - 美元引号内的分号忽略：      $$ body; $$ 和 $tag$ body; $tag$
///  - 自动 trim 并过滤空语句

// ── 状态机 ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
enum LexState {
    Normal,
    SingleQuote,  // 在 '...' 中
    DoubleQuote,  // 在 "..." 中
    LineComment,  // 在 -- ... 换行 中
    BlockComment, // 在 /* ... */ 中（支持嵌套）
    DollarQuote,  // 在 $tag$...$tag$ 中，tag 存于 dollar_tag
}

// ── 辅助：从位置 i 尝试解析美元引号标签 $tag$ ──────────────────────────────
//
// 返回 Some(tag_str, end_pos)，其中 end_pos 是第二个 $ 之后的位置。
// 合法标签字符：字母、数字、下划线（PostgreSQL 规范）。
// $$ 是 tag 为空字符串的特例。
fn try_parse_dollar_tag(bytes: &[u8], start: usize) -> Option<(String, usize)> {
    // bytes[start] 必须是 b'$'
    debug_assert_eq!(bytes[start], b'$');

    let mut j = start + 1;
    while j < bytes.len() {
        match bytes[j] {
            b'$' => {
                // 找到结束的 $，提取标签
                let tag = std::str::from_utf8(&bytes[start + 1..j]).ok()?;
                // 验证标签字符合法（字母 / 数字 / 下划线，首字符不能是数字）
                let valid = tag.is_empty() || {
                    let mut chars = tag.chars();
                    let first = chars.next().unwrap();
                    (first.is_alphabetic() || first == '_')
                        && chars.all(|c| c.is_alphanumeric() || c == '_')
                };
                if valid {
                    return Some((tag.to_string(), j + 1));
                } else {
                    return None;
                }
            }
            b if b.is_ascii_alphanumeric() || b == b'_' => {
                j += 1;
            }
            _ => return None, // 非法字符，不是美元引号
        }
    }
    None
}

// ── 核心：split_sql ───────────────────────────────────────────────────────────

/// 对单个大字符串进行 SQL 分割，返回 SQL 语句列表。
/// 所有语句已 trim，空语句被过滤掉。
/// 返回的切片零拷贝，直接引用原始 `input`。

pub fn split_sql(input: &str) -> Vec<&str> {
    let bytes = input.as_bytes();
    let len = bytes.len();

    let mut result = Vec::new();
    let mut state = LexState::Normal;
    let mut block_depth: u32 = 0;
    let mut dollar_tag = String::new();
    let mut stmt_start = 0usize;
    let mut i = 0usize;

    while i < len {
        let b = bytes[i];
        let nxt = if i + 1 < len { bytes[i + 1] } else { 0 };

        match state {
            // ── Normal ────────────────────────────────────────────────────
            LexState::Normal => match b {
                b'\'' => state = LexState::SingleQuote,
                b'"' => state = LexState::DoubleQuote,
                b'-' if nxt == b'-' => state = LexState::LineComment,
                b'/' if nxt == b'*' => {
                    state = LexState::BlockComment;
                    block_depth = 1;
                    i += 1;
                },
                b'$' => {
                    if let Some((tag, end)) = try_parse_dollar_tag(bytes, i) {
                        dollar_tag = tag;
                        state = LexState::DollarQuote;
                        i = end; // 
                        continue;
                    }
                },
                b';' => {
                    let stmt = input[stmt_start..i].trim();
                    if !stmt.is_empty() {
                        result.push(stmt);
                    }
                    stmt_start = i + 1;
                },
                _ => {},
            },

            // ── SingleQuote ───────────────────────────────────────────────
            LexState::SingleQuote => match b {
                b'\'' if nxt == b'\'' => i += 1, // 转义单引号''
                b'\\' if nxt == b'\'' => i += 1, // 转义单引号\'
                b'\'' => state = LexState::Normal,
                _ => {},
            },

            // ── DoubleQuote ───────────────────────────────────────────────
            LexState::DoubleQuote => match b {
                b'"' if nxt == b'"' => i += 1, // 转义双引号""
                b'"' => state = LexState::Normal,
                _ => {},
            },

            // ── LineComment ───────────────────────────────────────────────
            LexState::LineComment => {
                if b == b'\n' {
                    state = LexState::Normal;
                }
            },

            // ── BlockComment （支持嵌套）────────────────────────────────────
            LexState::BlockComment => {
                if b == b'/' && nxt == b'*' {
                    block_depth += 1;
                    i += 1;
                } else if b == b'*' && nxt == b'/' {
                    block_depth -= 1;
                    if block_depth == 0 {
                        state = LexState::Normal;
                    }
                    i += 1;
                }
            },

            // ── DollarQuote ───────────────────────────────────────────────
            // 寻找与开标签完全匹配的闭标签 $tag$
            LexState::DollarQuote => {
                if b == b'$' {
                    // 构造期望的闭标签字节序列：$tag$
                    let close = format!("${}$", dollar_tag);
                    let close_bytes = close.as_bytes();
                    if bytes[i..].starts_with(close_bytes) {
                        // 找到闭标签，跳过它
                        i += close_bytes.len(); // i 会在 continue 前不再 +1
                        state = LexState::Normal;
                        dollar_tag.clear();
                        continue;
                    }
                }
            },
        }

        i += 1;
    }

    // 末尾没有分号的最后一条语句
    let tail = input[stmt_start..].trim();
    if !tail.is_empty() {
        result.push(tail);
    }

    result
}

// ── 目录读取 ──────────────────────────────────────────────────────────────────

/// 从目录递归读取所有 .sql 文件，拼接为一个大字符串。
/// 返回 (拼接内容, 读取的文件数)。
pub fn read_sql_dir(dir: &std::path::Path) -> std::io::Result<(String, usize)> {
    use std::fs;
    use walkdir::WalkDir;

    let entries: Vec<_> = WalkDir::new(dir)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .filter(|e| {
            e.path()
                .extension()
                .and_then(|ext| ext.to_str())
                .is_some_and(|ext| ext.eq_ignore_ascii_case("sql"))
        })
        .collect();

    let count = entries.len();
    // 预估容量，减少重分配
    let estimated_size = count * 5 * 1024; // 假设每个文件平均 5KB
    let mut combined = String::with_capacity(estimated_size);

    for entry in entries {
        let content = fs::read_to_string(entry.path())?;
        combined.push_str(&content);
        combined.push('\n'); // 文件间添加换行，避免拼接后语句连在一起
    }

    Ok((combined, count))
}

// ── 单元测试 ──────────────────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_split() {
        let sql = "SELECT 1; SELECT 2; SELECT 3";
        assert_eq!(split_sql(sql), vec!["SELECT 1", "SELECT 2", "SELECT 3"]);
    }

    #[test]
    fn test_semicolon_in_single_quote() {
        let sql = "INSERT INTO t VALUES('a;b;c'); SELECT 1";
        assert_eq!(
            split_sql(sql),
            vec!["INSERT INTO t VALUES('a;b;c')", "SELECT 1"]
        );
    }

    #[test]
    fn test_escaped_single_quote() {
        let sql = "SELECT 'it''s ok'; SELECT 1";
        assert_eq!(split_sql(sql), vec!["SELECT 'it''s ok'", "SELECT 1"]);
    }

    #[test]
    fn test_double_quote_identifier() {
        let sql = r#"SELECT "col;name" FROM t; SELECT 2"#;
        assert_eq!(
            split_sql(sql),
            vec![r#"SELECT "col;name" FROM t"#, "SELECT 2"]
        );
    }

    #[test]
    fn test_line_comment() {
        let sql = "SELECT 1; -- comment; still\nSELECT 2";
        assert_eq!(
            split_sql(sql),
            vec!["SELECT 1", "-- comment; still\nSELECT 2"]
        );
    }

    #[test]
    fn test_block_comment() {
        let sql = "SELECT /* comment; inside */ 1; SELECT 2";
        assert_eq!(
            split_sql(sql),
            vec!["SELECT /* comment; inside */ 1", "SELECT 2"]
        );
    }

    #[test]
    fn test_nested_block_comment() {
        // PostgreSQL 支持嵌套块注释
        let sql = "SELECT /* outer /* inner; */ still; comment */ 1; SELECT 2";
        assert_eq!(
            split_sql(sql),
            vec![
                "SELECT /* outer /* inner; */ still; comment */ 1",
                "SELECT 2"
            ]
        );
    }

    #[test]
    fn test_empty_statements_filtered() {
        let sql = "SELECT 1;;;SELECT 2;;";
        assert_eq!(split_sql(sql), vec!["SELECT 1", "SELECT 2"]);
    }

    // ── 美元引号测试 ──────────────────────────────────────────────────────────

    #[test]
    fn test_dollar_quote_basic() {
        // $$ 是最常见形式
        let sql =
            "CREATE FUNCTION f() RETURNS void AS $$ BEGIN; END; $$ LANGUAGE plpgsql; SELECT 1";
        let result = split_sql(sql);
        assert_eq!(result.len(), 2);
        assert!(result[0].starts_with("CREATE FUNCTION"));
        assert_eq!(result[1], "SELECT 1");
    }

    #[test]
    fn test_dollar_quote_with_tag() {
        // $body$ 标签形式
        let sql = "CREATE FUNCTION f() RETURNS void AS $body$ BEGIN; RETURN; END; $body$ LANGUAGE plpgsql; SELECT 2";
        let result = split_sql(sql);
        assert_eq!(result.len(), 2);
        assert!(result[0].contains("$body$"));
        assert_eq!(result[1], "SELECT 2");
    }

    #[test]
    fn test_dollar_quote_nested() {
        // 外层 $outer$，内层 $$（PG 允许不同标签嵌套）
        let sql = concat!(
            "CREATE FUNCTION outer_fn() RETURNS void AS $outer$\n",
            "  EXECUTE $$ SELECT; 1 $$;\n",
            "$outer$ LANGUAGE plpgsql;\n",
            "SELECT 3"
        );
        let result = split_sql(sql);
        assert_eq!(result.len(), 2, "got: {result:?}");
        assert_eq!(result[1], "SELECT 3");
    }

    #[test]
    fn test_dollar_not_confused_with_parameter() {
        // $1 $2 是 PG 参数占位符，不是美元引号
        let sql = "SELECT $1, $2 FROM t; SELECT 1";
        assert_eq!(split_sql(sql), vec!["SELECT $1, $2 FROM t", "SELECT 1"]);
    }

    #[test]
    fn test_dollar_quote_multiline_body() {
        let sql = "DO $$ DECLARE\n  x int := 1;\nBEGIN\n  RAISE NOTICE '%', x;\nEND $$; SELECT 1";
        let result = split_sql(sql);
        assert_eq!(result.len(), 2);
        assert_eq!(result[1], "SELECT 1");
    }
}
