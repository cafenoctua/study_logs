
use crate::operator::Operator;
use crate::error::CalcError;

#[derive(Debug, PartialEq)]
pub struct Expression {
    pub numbers: Vec<i32>,
    pub operators: Vec<Operator>,
}

impl Expression {
    pub fn parse(args: Vec<String>) -> Result<Self, CalcError> {
        // claude solution
        if args.len() < 3 || args.len() % 2 == 0 {
            return Err(CalcError::InsufficientArgs);
        }

        let numbers: Result<Vec<i32>, CalcError> = args
            .iter()
            .step_by(2)
            .map(|s| {
                s.parse::<i32>()
                    .map_err(|_| CalcError::InvalidNumber(s.clone()))
                    .and_then(|n| {
                        if n < -1000 || n > 1000 {
                            Err(CalcError::NumberOutOfRange(n))
                        } else {
                            Ok(n)
                        }
                    })
            })
            .collect();

        let operators: Result<Vec<Operator>, CalcError> = args
            .iter()
            .skip(1)
            .step_by(2)
            .map(|s| s.parse::<Operator>())
            .collect();
        
        Ok(Self {
            numbers: numbers?,
            operators: operators?
        })

        // My implementation
        // let mut nums: Vec<i32> = vec![];
        // for (i, num) in args.iter().enumerate() {
        //     if i % 2 == 0 {
        //         nums.push(num.trim().parse().expect("Input number"));
        //     }
        // }

        // let mut formulas: Vec<String> = vec![];
        // for (i, formula) in args.iter().enumerate() {
        //     if i % 2 == 1 {
        //         formulas.push(String::from(formula));
        //     }
        // }

        // (nums, formulas)
    }

    pub fn evaluate(&self) -> Result<i32, CalcError> {
        let mut result = self.numbers[0];
        
        for (num, op) in self.numbers.iter().skip(1).zip(self.operators.iter()) {
            result= op.calculate(result, *num)?;
        }

        Ok(result)
    }
}