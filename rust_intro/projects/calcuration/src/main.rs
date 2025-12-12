use std::env;

mod error;
use error::CalcError;

mod operator;
use operator::Operator;

mod expression;
use expression::Expression;

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();

    match run(args) {
        Ok(result) => println!("Result: {}", result),
        Err(e) => {
            panic!("Error: {}", e);
        }
    }
}

fn run(args: Vec<String>) -> Result<i32, CalcError> {
    let expr = Expression::parse(args)?;
    expr.evaluate()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_1_to_1() {
        let expr = Expression::parse(
            vec![String::from("1"), String::from("+"), String::from("1")]
            ).unwrap();
        assert_eq!(Ok(2), expr.evaluate());
    }

    #[test]
    fn add_1_to_minus_1() {
        let expr = Expression::parse(
            vec![String::from("1"), String::from("+"), String::from("-1")]
            ).unwrap();
        assert_eq!(Ok(0), expr.evaluate());
    }

    #[test]
    fn subtract_1_to_1() {
        let expr = Expression::parse(
            vec![String::from("1"), String::from("-"), String::from("1")]
            ).unwrap();
        assert_eq!(Ok(0), expr.evaluate());
    }


    #[test]
    fn subtract_minus_1_to_1() {
        let expr = Expression::parse(
            vec![String::from("-1"), String::from("-"), String::from("1")]
            ).unwrap();
        assert_eq!(Ok(-2), expr.evaluate());
    }

    #[test]
    fn multiply_2_to_2() {
        let expr = Expression::parse(
            vec![String::from("2"), String::from("+"), String::from("2")]
            ).unwrap();
        assert_eq!(Ok(4), expr.evaluate());
    }

    #[test]
    fn multiply_minus_2_to_2() {
        let expr = Expression::parse(
            vec![String::from("-2"), String::from("-"), String::from("2")]
            ).unwrap();
        assert_eq!(Ok(-4), expr.evaluate());
    }

    #[test]
    fn multiply_minus_2_to_minus_2() {
        let expr = Expression::parse(
            vec![String::from("-2"), String::from("*"), String::from("-2")]
            ).unwrap();
        assert_eq!(Ok(4), expr.evaluate());
    }

    #[test]
    fn division_4_to_2() {
        let expr = Expression::parse(
            vec![String::from("4"), String::from("/"), String::from("2")]
            ).unwrap();
        assert_eq!(Ok(2), expr.evaluate());
    }

    #[test]
    fn division_minus_4_to_2() {
        let expr = Expression::parse(
            vec![String::from("-4"), String::from("/"), String::from("2")]
            ).unwrap();
        assert_eq!(Ok(-2), expr.evaluate());
    }

    #[test]
    fn division_minus_4_to_minus_2() {
        let expr = Expression::parse(
            vec![String::from("-4"), String::from("/"), String::from("-2")]
            ).unwrap();
        assert_eq!(Ok(2), expr.evaluate());
    }

    #[test]
    fn division_1_to_2() {
        let expr = Expression::parse(
            vec![String::from("1"), String::from("/"), String::from("2")]
            ).unwrap();
        assert_eq!(Ok(0), expr.evaluate());
    }

    #[test]
    fn args_less_than_3() {
        let input = vec![String::from("1")];
        let args = Expression::parse(input);
        assert_eq!(Err(CalcError::InvalidFormat), args);
    }
    
    #[test]
    fn correct_device_formula() {
        let input = vec![String::from("1"), String::from("+"), String::from("1")];
        assert_eq!(
            Ok(Expression{numbers: vec![1, 1], operators: vec![Operator::Add]}),
            Expression::parse(input)
        );
    }

    #[test]
    fn calc_add_result() {
        let input = vec![String::from("1"), String::from("+"), String::from("1")];
        let expr = Expression::parse(input).unwrap();

        let result = expr.evaluate();

        assert_eq!(Ok(2), result);
    }

    #[test]
    fn calc_add_output_3() {
        let input = vec![String::from("1"), String::from("+"), String::from("1"), String::from("+"), String::from("1")];
        let expr = Expression::parse(input).unwrap();

        let result = expr.evaluate();

        assert_eq!(Ok(3), result);
    }

}