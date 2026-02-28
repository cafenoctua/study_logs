enum Message {
    Text(String),
    Number(i32),
    Quit,
}

impl Message {
    fn process(&self) -> String {
        // TODO: メッセージの種類に応じて処理
        // Text: 文字列を出力
        // Number: 数値を2倍して出力
        // Quit: "終了します"と出力
        match self {
            Message::Text(state) => String::from(state),
            Message::Number(state) => {
                let result = state * 2;
                let result_str = result.to_string();
                result_str
            }
            Message::Quit => String::from("終了します"),
        }
    }
}

fn main() {
    let messages = vec![
        Message::Text(String::from("こんにちは")),
        Message::Number(42),
        Message::Quit,
    ];

    for msg in messages {
        println!("{}", msg.process());
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_output_text() {
        let msg = Message::Text(String::from("test"));
        assert_eq!("test", msg.process());
    }

    #[test]
    fn test_output_space() {
        let msg = Message::Text(String::from(""));
        assert_eq!("", msg.process());
    }

    #[test]
    fn test_output_multiply_2() {
        let msg = Message::Number(2);
        assert_eq!("4", msg.process());
    }

    #[test]
    fn test_output_multiply_0() {
        let msg = Message::Number(0);
        assert_eq!("0", msg.process());
    }

    #[test]
    fn test_output_quit() {
        let msg = Message::Quit;
        assert_eq!("終了します", msg.process());
    }
}
