fn count_words(s: &str) -> usize {
    // TODO(human): イテレータの.count()メソッドを使って単語数をカウントしてください
    // ヒント: s.split_whitespace().count()

    //let words = s.split_whitespace();

    //let mut s_len: usize = 0;
    //for word in words {
    //    s_len += word.len()
    //}
    //s_len

    s.split_whitespace().count()
}

fn main() {
    let text = String::from("Hello Rust world");
    let count = count_words(&text);
    println!("単語数: {}", count);
    println!("元の文字列: {}", text); // textがまだ使える
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn input_0_output_0() {
        assert_eq!(0, count_words(""));
    }

    #[test]
    fn input_continuous_words() {
        assert_eq!(1, count_words("abcde"));
    }

    #[test]
    fn input_white_space() {
        assert_eq!(2, count_words("a b"));
    }

    #[test]
    fn input_muiltiple_spaces() {
        assert_eq!(2, count_words("Hello      world"));
    }

    #[test]
    fn input_leading_trailing_spaces() {
        assert_eq!(2, count_words("  Hello      world   "));
    }

    #[test]
    fn input_three_words() {
        assert_eq!(3, count_words("Hello Rust      world"));
    }

    #[test]
    fn input_tab_and_newline() {
        assert_eq!(3, count_words("Rust\tRust\nworld"));
    }
}
