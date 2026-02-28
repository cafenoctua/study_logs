fn find_max(numbers: &[i32]) -> Option<i32> {
    // let mut max_num: i32 = numbers[0];

    // for &i in &numbers[1..] {
    //     if max_num < i {
    //         max_num = i;
    //     }
    // }

    // max_num
    
    //if numbers.is_empty() {
    //    return None;
    //}

    //Some(*numbers.iter().max().unwrap())
    
    numbers.iter().max().copied()
}

fn main() {
    let numbers = [34, 50, 25, 100, 65];
    match find_max(&numbers) {
        Some(max) => println!("最大値: {}", max),
        None => println!("配列が空です"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn input_0_output_0() {
        assert_eq!(Some(0), find_max(&[0]));
    }

    #[test]
    fn input_minus_1_to_0_output_0() {
        assert_eq!(Some(0), find_max(&[-1, 0])); 
    }

    #[test]
    fn input_100_in_array_output_100() {
        assert_eq!(Some(100), find_max(&[100, 0, 1])); 
    }

    #[test]
    fn input_empty_array_output_none() {
        assert_eq!(None, find_max(&[]));
    }
}
