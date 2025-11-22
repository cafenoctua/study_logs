

use std::env;


#[derive(Debug)]
#[derive(PartialEq)]
struct Input {
    start_num: i32,
    countup: i32,
}

impl Input {
    fn new(args: &[String]) -> Result<Input, &'static str> {
        if args.len() < 3 {
            return Err("Not enought arguments");
        }

        let start_num: i32 = args[1].trim().parse().expect("input number");
        if start_num < 0 || start_num > 1000 { return Err("Input range in 0 ~ 1000");}

        let countup: i32 = args[2].trim().parse().expect("input number");
        if countup < 0 || countup > 1000 { return Err("Input range in 0 ~ 1000");}

        Ok(Input { start_num: start_num, countup: countup })
    }

    fn _valid_input() -> Result<Input, &'static str> {
        Ok(Input { start_num: 0, countup: 0 })
    }

    fn _invalid_input_number() -> Result<Input, &'static str> {
        Err("Input range in 0 ~ 1000")
    }
}

fn countup(input: Input) -> Vec<i32> {
    if input.countup == 0 {
        return vec![input.start_num];
    }

    let mut countup_list = vec![];
    for i in input.start_num..(input.start_num+input.countup) {
        countup_list.push(i);
    }

    countup_list
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let input = Input::new(&args);
    println!("{:?}", countup(input.unwrap()));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn check_output_0() {
        let args: Vec<String> = vec![String::from(""), String::from("0"), String::from("0")];
        let input = Input::new(&args);
        let output = countup(input.unwrap());
        assert_eq!(vec![0], output);
    }

    #[test]
    fn check_output_1_to_10() {
        let args: Vec<String> = vec![String::from(""), String::from("1"), String::from("10")];
        let input = Input::new(&args);
        let output = countup(input.unwrap());
        assert_eq!(vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10], output);
    }

    #[test]
    fn start_num_input_minus() {
        let args: Vec<String> = vec![String::from(""), String::from("-1"), String::from("0")];
        let input = Input::new(&args);
        assert_eq!(Input::_invalid_input_number(), input);
    }

    #[test]
    fn countup_input_minus() {
        let args: Vec<String> = vec![String::from(""), String::from("0"), String::from("-1")];
        let input = Input::new(&args);
        assert_eq!(Input::_invalid_input_number(), input);
    }

    #[test]
    fn start_num_input_more_than_10000() {
        let args: Vec<String> = vec![String::from(""), String::from("1001"), String::from("0")];
        let input = Input::new(&args);
        assert_eq!(Input::_invalid_input_number(), input);
    }

    #[test]
    fn countup_input_more_than_10000() {
        let args: Vec<String> = vec![String::from(""), String::from("0"), String::from("1001")];
        let input = Input::new(&args);
        assert_eq!(Input::_invalid_input_number(), input);
    }

    #[test]
    fn test_input_valid_arguments() {
        let args: Vec<String> = vec![String::from(""), String::from("0"), String::from("0")];
        let input = Input::new(&args);
        assert_eq!(Input::_valid_input(), input);
    }
    

}