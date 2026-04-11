use std::fmt;

#[derive(Debug, PartialEq)]
pub enum CalcError {
    InsufficientArgs,
    InvalidNumber(String),
    InvalidOperator(String),
    DivisionByZero,
    NumberOutOfRange(i32),
    InvalidFormat,
}

impl fmt::Display for CalcError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CalcError::InsufficientArgs => write!(f, "引数が不足しています"),
            CalcError::InvalidNumber(s) => write!(f, "無効な数値: {}", s),
            CalcError::InvalidOperator(s) => write!(f, "無効な演算子: {}", s),
            CalcError::DivisionByZero => write!(f, "ゼロ除算エラー"),
            CalcError::NumberOutOfRange(n) => write!(f, "範囲外の数値: {} (-10000~10000)", n),
            CalcError::InvalidFormat => write!(f, "入力形式が不正です"),
        }
    }
}