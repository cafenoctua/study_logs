use std::fmt;

#[derive(Debug)]
enum PasswordError {
    TooShort(usize), // 現在の長さを含む
    NoUppercase,
    NoLowercase,
    NoDigit,
}

impl fmt::Display for PasswordError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // TODO: エラーメッセージを実装
        match self {
            PasswordError::TooShort(state) => write!(
                f,
                "This Password length is {}. It's too shoot please set more than 8 characters.",
                state
            ),
            PasswordError::NoUppercase => write!(f, "This Password not include Uppercase."),
            PasswordError::NoLowercase => write!(f, "This Password not include Lowercase."),
            PasswordError::NoDigit => write!(f, "This Password not include digit."),
        }
    }
}

fn validate_password(password: &str) -> Result<(), PasswordError> {
    // TODO: 実装
    // 条件: 8文字以上、大文字・小文字・数字を含む

    // 8文字以上か検証
    if password.len() < 8 {
        return Err(PasswordError::TooShort(password.len()));
    }

    // 大文字含むか検証
    if !password.chars().any(|c| c.is_uppercase()) {
        return Err(PasswordError::NoUppercase);
    }

    // 小文字含むか検証
    if !password.chars().any(|c| c.is_lowercase()) {
        return Err(PasswordError::NoLowercase);
    }

    // 数字含むか検証
    if !password.chars().any(|c| c.is_digit(10)) {
        return Err(PasswordError::NoDigit);
    }

    // 検証全てクリアしたら成功値を返す
    Ok(())
}

fn main() {
    let passwords = [
        "short",
        "alllowercase",
        "ALLUPPERCASE",
        "NoDigits",
        "Valid1Pass",
    ];

    for pw in passwords {
        match validate_password(pw) {
            Ok(()) => println!("{}: OK", pw),
            Err(e) => println!("{}: {}", pw, e),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn input_valid_password() {
        let password = "Valid1Pass";

        let result = validate_password(password);

        assert!(result.is_ok());
    }

    #[test]
    fn input_invalid_password() {
        let invalid_passwords = ["short", "alllowercase1", "ALLUPPERCASE1", "NoDigitsHere"];

        for password in invalid_passwords {
            let result = validate_password(password);
            assert!(result.is_err(), "Password '{}' should be invalid", password);
        }
    }

    #[test]
    fn input_password_too_short() {
        let result = validate_password("short");

        assert!(result.is_err());
        assert!(matches!(result, Err(PasswordError::TooShort(5))));
    }

    #[test]
    fn input_password_no_uppercase() {
        let result = validate_password("alllowercase1");

        assert!(result.is_err());
        assert!(matches!(result, Err(PasswordError::NoUppercase)));
    }

    #[test]
    fn input_password_no_lowercase() {
        let result = validate_password("ALLUPPERCASE1");

        assert!(result.is_err());
        assert!(matches!(result, Err(PasswordError::NoLowercase)));
    }

    #[test]
    fn input_password_no_digit() {
        let result = validate_password("NoDigitsHere");

        assert!(result.is_err());
        assert!(matches!(result, Err(PasswordError::NoDigit)));
    }
}
