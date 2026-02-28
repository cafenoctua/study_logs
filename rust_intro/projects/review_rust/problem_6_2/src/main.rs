fn sum_evens_squared(numbers: Vec<i32>) -> i32 {
    numbers.iter().filter(|&x| x % 2 == 0).map(|&x| x * x).sum()
}

fn main() {
    let numbers = vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

    // TODO: 偶数だけをフィルタし、それぞれ2乗して、合計を求める
    // 結果: 2^2 + 4^2 + 6^2 + 8^2 + 10^2 = 220
    let result: i32 = sum_evens_squared(numbers);

    println!("結果: {}", result);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_input_0_output_0() {
        assert_eq!(0, sum_evens_squared(vec![0]));
    }

    #[test]
    fn test_input_no_evens_output_0() {
        assert_eq!(0, sum_evens_squared(vec![1, 3]));
    }

    #[test]
    fn test_input_2_output_4() {
        assert_eq!(4, sum_evens_squared(vec![2]));
    }

    #[test]
    fn test_input_1_to_4_output_20() {
        assert_eq!(20, sum_evens_squared(vec![1, 2, 3, 4]));
    }
}
