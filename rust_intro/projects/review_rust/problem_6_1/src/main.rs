struct EvenNumbers {
    current: u32,
    max: u32,
}

impl EvenNumbers {
    fn new(max: u32) -> Self {
        // TODO
        Self { current: 0, max }
    }
}

impl Iterator for EvenNumbers {
    type Item = u32;

    fn next(&mut self) -> Option<Self::Item> {
        // TODO
        self.current += 2;
        if self.current <= self.max {
            Some(self.current)
        } else {
            None
        }
    }
}

fn main() {
    let evens = EvenNumbers::new(10);
    for n in evens {
        println!("{}", n);
    }
    // 出力: 2, 4, 6, 8, 10
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_output_2() {
        let mut evens = EvenNumbers::new(2);
        assert_eq!(Some(2), evens.next());
    }

    #[test]
    fn test_output_even() {
        let mut evens = EvenNumbers::new(4);
        assert_eq!(Some(2), evens.next());
        assert_eq!(Some(4), evens.next());
    }

    #[test]
    fn test_input_0_output_none() {
        let mut evens = EvenNumbers::new(0);

        assert_eq!(None, evens.next());
    }

    #[test]
    fn test_input_3_last_output_none() {
        let mut evens = EvenNumbers::new(3);

        evens.next();
        assert_eq!(None, evens.next());
    }
}
