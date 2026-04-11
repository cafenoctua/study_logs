use std::str::FromStr;
use crate::error::CalcError;

#[derive(Debug, PartialEq)]
pub enum  Operator{
    Add,
    Subtract,
    Multiply,
    Divide,
}

impl FromStr for Operator {
    type Err = CalcError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "+" => Ok(Operator::Add),
            "-" => Ok(Operator::Subtract),
            "*" => Ok(Operator::Multiply),
            "/" => Ok(Operator::Divide),
            _ => Err(CalcError::InvalidOperator(s.to_string())),
        }
    }
}

impl Operator {
    pub fn calculate(&self, a: i32, b: i32) -> Result<i32, CalcError>{
        match self {
            Operator::Add => Ok(a + b),
            Operator::Subtract => Ok(a - b),
            Operator::Multiply => Ok(a * b),
            Operator::Divide => {
                if b == 0 {
                    Err(CalcError::DivisionByZero)
                } else {
                    Ok(a / b)
                }
            }
        }
    }
}
