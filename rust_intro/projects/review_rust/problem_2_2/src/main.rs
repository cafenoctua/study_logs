fn longest<'a>(s1: &'a str, s2: &'a str) -> &'a str {
    // TODO: 実装してください
    if s1.len() < s2.len() {
        return s2;
    }

    s1
}

fn main() {
    let s1 = String::from("short");
    let s2 = String::from("longer string");
    println!("長い方: {}", longest(&s1, &s2));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn input_space() {
        assert_eq!("test", longest("", "test"));
    }

    #[test]
    fn input_same_length() {
        assert_eq!("first", longest("first", "third"));
    }

    #[test]
    fn input_space_both() {
        assert_eq!("", longest("", ""));
    }
}
