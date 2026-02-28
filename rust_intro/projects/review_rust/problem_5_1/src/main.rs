struct Stack<T> {
    items: Vec<T>,
}

impl<T> Stack<T> {
    fn new() -> Self {
        // TODO
        Stack { items: vec![] }
    }

    fn push(&mut self, item: T) {
        // TODO
        self.items.push(item);
    }

    fn pop(&mut self) -> Option<T> {
        // TODO
        self.items.pop()
    }

    fn peek(&self) -> Option<&T> {
        // TODO
        self.items.last()
    }

    fn is_empty(&self) -> bool {
        // TODO
        self.items.is_empty()
    }

    fn len(&self) -> usize {
        // TODO
        self.items.len()
    }
}

fn main() {
    let mut stack: Stack<i32> = Stack::new();
    stack.push(1);
    stack.push(2);
    stack.push(3);

    println!("最後の要素: {}", stack.peek().unwrap());
    println!("空配列か？: {}", stack.is_empty());
    println!("配列のサイズ: {}", stack.len());

    while let Some(value) = stack.pop() {
        println!("{}", value);
    }
}

#[cfg(test)]
mod tests {
    use crate::Stack;

    #[test]
    fn test_push_pop() {
        let mut stack: Stack<i32> = Stack::new();
        stack.push(1);
        assert_eq!(Some(1), stack.pop());
    }

    #[test]
    fn test_peek() {
        let mut stack: Stack<i32> = Stack::new();
        stack.push(1);
        stack.push(2);
        assert_eq!(Some(2), stack.pop());
    }

    #[test]
    fn test_empty() {
        let stack: Stack<i32> = Stack::new();
        assert_eq!(true, stack.is_empty());
    }

    #[test]
    fn test_is_not_empty() {
        let mut stack: Stack<i32> = Stack::new();
        stack.push(1);
        assert_eq!(false, stack.is_empty());
    }

    #[test]
    fn test_vec_len() {
        let mut stack: Stack<i32> = Stack::new();
        stack.push(1);
        assert_eq!(1, stack.len());
    }

    #[test]
    fn test_brank_vec_len() {
        let stack: Stack<i32> = Stack::new();
        assert_eq!(0, stack.len());
    }
}
