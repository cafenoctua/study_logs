use std::collections::HashMap;

#[derive(Debug, PartialEq)]
struct HttpResponse {
    status_code: u16,
    headers: HashMap<String, String>,
    body: String,
}

#[derive(Debug, PartialEq)]
enum ParseError {
    InvalidStatusLine,
    InvalidHeader,
    EmptyResponse,
}

impl HttpResponse {
    fn parse(response: &str) -> Result<Self, ParseError> {
        // TODO: 実装
        // 形式:
        // HTTP/1.1 200 OK
        // Content-Type: text/plain
        // Content-Length: 13
        //
        // Hello, World!

        if response.is_empty() {
            return Err(ParseError::EmptyResponse);
        }

        let mut lines = response.lines();

        // ステータスライン
        let status_line = lines.next().ok_or(ParseError::InvalidStatusLine)?;
        let mut parts = status_line.split_whitespace();
        let _version = parts.next().ok_or(ParseError::InvalidStatusLine)?;
        let status_code = parts
            .next()
            .ok_or(ParseError::InvalidStatusLine)?
            .parse::<u16>()
            .map_err(|_| ParseError::InvalidStatusLine)?;

        // ヘッダー
        let mut headers = HashMap::new();
        for line in &mut lines {
            if line.trim().is_empty() {
                break;
            }
            let (key, value) = line.split_once(':').ok_or(ParseError::InvalidHeader)?;
            headers.insert(key.trim().to_string(), value.trim().to_string());
        }

        // ボディー
        let body = lines.collect::<Vec<_>>().join("\n");

        Ok(Self {
            status_code,
            headers,
            body,
        })
    }
}

fn main() {
    let response = r#"HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 13

Hello, World!"#;

    match HttpResponse::parse(response) {
        Ok(resp) => {
            println!("Status: {}", resp.status_code);
            println!("Headers: {:?}", resp.headers);
            println!("Body: {}", resp.body);
        }
        Err(e) => println!("Parse error: {:?}", e),
    }
}

#[cfg(test)]
mod tests {

    use super::*;

    #[test]
    fn test_success_parce() {
        let expect = HttpResponse {
            status_code: 200,
            headers: {
                let mut h = HashMap::new();
                h.insert("Content-Type".to_string(), "text/plain".to_string());
                h.insert("Content-Length".to_string(), "13".to_string());
                h
            },
            body: "Hello, World!".to_string(),
        };

        let response = r#"HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 13

Hello, World!"#;

        let parse_result = HttpResponse::parse(response);
        assert_eq!(Ok(expect), parse_result);
    }

    #[test]
    fn test_success_parce_body_with_carriage_return() {
        let expect = HttpResponse {
            status_code: 200,
            headers: {
                let mut h = HashMap::new();
                h.insert("Content-Type".to_string(), "text/plain".to_string());
                h.insert("Content-Length".to_string(), "13".to_string());
                h
            },
            body: r#"Hello, World!

Test body

body 1 2 3"#
                .to_string(),
        };

        let response = r#"HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 13

Hello, World!

Test body

body 1 2 3"#;
        let parse_result = HttpResponse::parse(response);
        assert_eq!(Ok(expect), parse_result);
    }

    #[test]
    fn test_input_empty_response() {
        let response = "";

        let parse_result = HttpResponse::parse(response);
        assert!(parse_result.is_err_and(|e| e == ParseError::EmptyResponse));
    }

    #[test]
    fn test_input_invalid_status_lines() {
        let response = "HTTP/1.1";

        let parse_result = HttpResponse::parse(response);
        assert!(parse_result.is_err_and(|e| e == ParseError::InvalidStatusLine));
    }

    #[test]
    fn test_input_invalid_status_code() {
        let response = "HTTP/1.1 a OK";

        let parse_result = HttpResponse::parse(response);
        assert!(parse_result.is_err_and(|e| e == ParseError::InvalidStatusLine));
    }

    #[test]
    fn test_input_invalid_headers() {
        let response = r#"HTTP/1.1 200 OK
Content-Typetext/plain
Content-Length13"#;

        let parse_result = HttpResponse::parse(response);
        assert!(parse_result.is_err_and(|e| e == ParseError::InvalidHeader));
    }
}
