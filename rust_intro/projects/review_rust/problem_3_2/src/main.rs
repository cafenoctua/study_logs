enum Operation {
    Add,
    Subtract,
    Multiply,
    Divide,
}

impl Operation {
    fn calculate(&self, a: i32, b: i32) -> Option<i32> {
        // TODO: 実装（0除算はNoneを返す）
        match self {
            Operation::Add => Some(a + b),
            Operation::Subtract => Some(a - b),
            Operation::Multiply => Some(a * b),
            Operation::Divide => {
                if b == 0 {
                    None
                } else {
                    Some(a / b)
                }
            }
        }
    }
}

fn main() {
    let ops = [
        (Operation::Add, 10, 5),
        (Operation::Subtract, 10, 5),
        (Operation::Multiply, 10, 5),
        (Operation::Divide, 10, 5),
        (Operation::Divide, 10, 0),
    ];

    for (op, a, b) in ops {
        match op.calculate(a, b) {
            Some(result) => println!("結果: {}", result),
            None => println!("計算エラー"),
        }
    }
}

#[cfg(test)]

mod tests {
    use super::*;

    #[test]
    fn add_op_normal() {
        let op = Operation::Add;
        assert_eq!(Some(2), op.calculate(1, 1));
    }

    #[test]
    fn add_op_minus() {
        let op = Operation::Add;
        assert_eq!(Some(0), op.calculate(1, -1));
    }

    #[test]
    fn substract_op_normal() {
        let op = Operation::Subtract;
        assert_eq!(Some(0), op.calculate(1, 1));
    }

    #[test]
    fn substract_op_minus() {
        let op = Operation::Subtract;
        assert_eq!(Some(2), op.calculate(1, -1));
    }

    #[test]
    fn multiply_op_normal() {
        let op = Operation::Multiply;
        assert_eq!(Some(1), op.calculate(1, 1));
    }

    #[test]
    fn multiply_op_minus() {
        let op = Operation::Multiply;
        assert_eq!(Some(-1), op.calculate(1, -1));
    }

    #[test]
    fn divide_op_normal() {
        let op = Operation::Divide;
        assert_eq!(Some(1), op.calculate(2, 2));
    }

    #[test]
    fn divide_op_minus() {
        let op = Operation::Divide;
        assert_eq!(Some(-1), op.calculate(2, -2));
    }

    #[test]
    fn divide_op_0() {
        let op = Operation::Divide;
        assert_eq!(None, op.calculate(2, 0));
    }
}
