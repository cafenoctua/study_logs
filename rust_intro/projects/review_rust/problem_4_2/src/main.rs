use std::fs::File;
use std::io::{self, BufRead, BufReader};

fn count_lines(filename: &str) -> Result<usize, io::Error> {
    // TODO: 実装
    // ヒント: File::open(), BufReader, lines()を使用

    let f = File::open(filename)?;
    let f = BufReader::new(f);

    Ok(f.lines().count())
}

fn main() {
    match count_lines("test.txt") {
        Ok(count) => println!("行数: {}", count),
        Err(e) => println!("エラー: {}", e),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_success_read_return_lines() {
        let result = count_lines("test.txt");

        assert!(result.is_ok(), "Expected Ok, got Err: {:?}", result);
        assert_eq!(2, result.unwrap());
    }

    #[test]
    fn test_error_read() {
        let result = count_lines("not_found.txt");

        assert!(result.is_err());
        if let Err(e) = result {
            assert_eq!(e.kind(), std::io::ErrorKind::NotFound);
        }
    }
}
