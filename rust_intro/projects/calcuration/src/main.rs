use std::env;

struct Args {
    args: Vec<String>,
}

impl Args {
    fn new(args: Vec<String>) -> Result<Vec<String>, &'static str>{
        if args.len() < 3 {
            return Err("Not enough arguments");
        }
        Ok(args)
    }

    fn devide_arguments(args: Vec<String>) -> (Vec<i32>, Vec<String>) {
        let mut nums: Vec<i32> = vec![];
        for (i, num) in args.iter().enumerate() {
            if i % 2 == 0 {
                nums.push(num.trim().parse().expect("Input number"));
            }
        }

        let mut formules: Vec<String> = vec![];
        for (i, formula) in args.iter().enumerate() {
            if i % 2 == 1 {
                formules.push(String::from(formula));
            }
        }

        (nums, formules)
    }

    fn _less_arguments() -> Result<Vec<String>, &'static str> {
        Err("Not enough arguments")
    }
}

fn add(a: i32, b: i32) -> i32 {
    return a + b;
}

fn diff(a: i32, b: i32) -> i32 {
    return a - b;
}

fn multiply(a: i32, b: i32) -> i32 {
    return a * b;
}

fn division(a: i32, b: i32) -> i32 {
    return a / b;
}

fn calcurator(nums: Vec<i32>, formules: Vec<String>) -> i32 {
    let mut result: i32 = nums[0];
    let nums_next: Vec<i32> = nums[1..].to_vec();
    for (i, _) in nums_next.iter().enumerate() {
        match formules[i].trim().as_ref() {
            "+" => result = add(result, nums_next[i]),
            "-" => result = diff(result, nums_next[i]),
            "*" => result = multiply(result, nums_next[i]),
            "/" => result = division(result, nums_next[i]),
            _ => continue
        };
    }

    result
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let input = Args::new(args[1..].to_vec());
    let (nums, formules) = Args::devide_arguments(input.unwrap());
    println!("Result: {}", calcurator(nums, formules));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_1_to_1() {
        assert_eq!(2, add(1, 1))
    }

    #[test]
    fn add_1_to_minus_1() {
        assert_eq!(0, add(1, -1))
    }

    #[test]
    fn diff_1_to_1() {
        assert_eq!(0, diff(1, 1));
    }


    #[test]
    fn diff_minus_1_to_1() {
        assert_eq!(-2, diff(-1, 1));
    }

    #[test]
    fn multiply_2_to_2() {
        assert_eq!(4, multiply(2, 2));
    }

    #[test]
    fn multiply_minus_2_to_2() {
        assert_eq!(-4, multiply(-2, 2));
    }

    #[test]
    fn multiply_minus_2_to_minus_2() {
        assert_eq!(4, multiply(-2, -2));
    }

    #[test]
    fn division_4_to_2() {
        assert_eq!(2, division(4, 2));
    }

    #[test]
    fn division_minus_4_to_2() {
        assert_eq!(-2, division(-4, 2));
    }

    #[test]
    fn division_minus_4_to_minus_2() {
        assert_eq!(2, division(4, 2));
    }

    #[test]
    fn division_1_to_2() {
        assert_eq!(0, division(1, 2));
    }

    #[test]
    fn args_less_than_3() {
        let input = vec![String::from("1")];
        let args = Args::new(input);
        assert_eq!(Args::_less_arguments(), args);
    }
    
    #[test]
    fn correct_device_formula() {
        let input = vec![String::from("1"), String::from("+"), String::from("1")];
        assert_eq!((vec![1, 1], vec![String::from("+")]), Args::devide_arguments(input));
    }

    #[test]
    fn calc_add_result() {
        let input = vec![String::from("1"), String::from("+"), String::from("1")];
        let (nums, formules) = Args::devide_arguments(input);

        let result = calcurator(nums, formules);

        assert_eq!(2, result);
    }

    #[test]
    fn calc_add_output_3() {
        let input = vec![String::from("1"), String::from("+"), String::from("1"), String::from("+"), String::from("1")];
        let (nums, formules) = Args::devide_arguments(input);

        let result = calcurator(nums, formules);

        assert_eq!(3, result);
    }

}