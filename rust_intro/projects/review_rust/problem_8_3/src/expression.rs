use crate::error::CalcError;
use crate::shunting_yard::{evaluate_rpn, to_rpn, tokenize, Token};

#[derive(Debug, PartialEq)]
pub struct Expression {
    pub Tokens: Vec<Token>,
}

impl Expression {
    pub fn parse(args: Vec<String>) -> Result<Self, CalcError> {
        // claude solution
        if args.len() < 3 {
            return Err(CalcError::InsufficientArgs);
        }

        let tokens = tokenize(&args)?;

        let rpm_output = to_rpn(tokens)?;
        Ok(Self { Tokens: rpm_output })
    }

    pub fn evaluate(&self) -> Result<i32, CalcError> {
        evaluate_rpn(&self.Tokens)
    }
}

