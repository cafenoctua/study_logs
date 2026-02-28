fn add_excitement(s: &mut String) {
    s.push_str("!");
}

fn main() {
    let mut message = String::from("Hello");
    add_excitement(&mut message);
    println!("{}", message); // "Hello!"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn input_space() {
        let mut m = String::from("");
        add_excitement(&mut m);
        assert_eq!(String::from("!"), m);
    }

    #[test]
    fn input_exitement() {
        let mut m = String::from("!");
        add_excitement(&mut m);
        assert_eq!(String::from("!!"), m);
    }

    #[test]
    fn input_normal_word() {
        let mut m = String::from("abc");
        add_excitement(&mut m);
        assert_eq!(String::from("abc!"), m);
    }

    #[test]
    fn input_text() {
        let mut m = String::from("Hello World");
        add_excitement(&mut m);
        assert_eq!(String::from("Hello World!"), m);
    }
}
