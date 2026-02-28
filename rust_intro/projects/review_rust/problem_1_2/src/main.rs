
fn judge_fizz_buzz(n: i32) -> String {
    if n % 15 == 0 {
        return "FizzBuzz".to_string();
    }


    if n % 3 == 0 {
        return "Fizz".to_string();
    }


    if n % 5 == 0 {
        return "Buzz".to_string();
    }

    n.to_string()
}

fn main() {
    // TODO: forループを使って実装してください
    for i in 1..31 {
       println!("{}", judge_fizz_buzz(i));
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    // TODO(human): 各テスト関数に#[test]属性を追加してください
    #[test]
    fn test_input_1_output_1() {
        assert_eq!("1".to_string(), judge_fizz_buzz(1));
    }

    #[test]
    fn test_input_15_output_fizzbuzz() {
        assert_eq!("FizzBuzz".to_string(), judge_fizz_buzz(15));
    }

    #[test]
    fn test_input_3_output_fizz() {
        assert_eq!("Fizz".to_string(), judge_fizz_buzz(3));
    }

    #[test]
    fn test_input_5_output_buzz() {
        assert_eq!("Buzz".to_string(), judge_fizz_buzz(5));
    }
}
