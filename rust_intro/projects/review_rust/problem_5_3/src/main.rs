use std::cmp::PartialOrd;

struct Pair<T> {
    first: T,
    second: T,
}

impl<T: PartialOrd> Pair<T> {
    fn new(first: T, second: T) -> Self {
        // TODO
        Self { first, second }
    }

    fn larger(&self) -> &T {
        // TODO
        if self.first > self.second {
            return &self.first;
        }

        &self.second
    }
}

trait HasLength {
    fn len(&self) -> usize;
}

impl HasLength for &str {
    fn len(&self) -> usize {
        str::len(self)
    }
}

impl HasLength for String {
    fn len(&self) -> usize {
        String::len(self)
    }
}

impl<T: HasLength> Pair<T> {
    fn longer(&self) -> &T {
        if self.first.len() > self.second.len() {
            return &self.first;
        }

        &self.second
    }
}

fn main() {
    let int_pair = Pair::new(15, 10);
    println!("大きい方: {}", int_pair.larger());

    let str_pair = Pair::new("appleaaaaaaa", "banana");
    println!("大きい方: {}", str_pair.longer());

    let string_pair = Pair::new(String::from("appleaaaaaaa"), String::from("banana"));
    println!("大きい方: {}", string_pair.longer());
}
