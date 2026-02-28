use std::collections::HashMap;

struct Cacher<T>
where
    T: Fn(u32) -> u32,
{
    calculation: T,
    values: HashMap<u32, u32>,
}

impl<T> Cacher<T>
where
    T: Fn(u32) -> u32,
{
    fn new(calculation: T) -> Self {
        // TODO
        let values = HashMap::new();
        Cacher {
            calculation,
            values,
        }
    }

    fn value(&mut self, arg: u32) -> u32 {
        // TODO: キャッシュがあれば返し、なければ計算してキャッシュ
        // if !self.values.contains_key(&arg) {
        //     self.values.insert(arg, (self.calculation)(arg));
        // }

        // self.values[&arg]

        *self
            .values
            .entry(arg)
            .or_insert_with(|| (self.calculation)(arg))
    }
}

fn main() {
    let mut expensive_calculation = Cacher::new(|n| {
        println!("計算中... {}", n);
        n * n
    });

    println!("結果: {}", expensive_calculation.value(5)); // 計算される
    println!("結果: {}", expensive_calculation.value(5)); // キャッシュから
    println!("結果: {}", expensive_calculation.value(3)); // 計算される
}

#[cfg(test)]
mod tests {
    use std::cell::Cell;

    use super::*;

    #[test]
    fn test_returns_correct_value() {
        let mut cacher = Cacher::new(|n| n * 2);
        assert_eq!(10, cacher.value(5));
    }

    #[test]
    fn test_caches_values() {
        let call_count = Cell::new(0);
        let mut cacher = Cacher::new(|n| {
            call_count.set(call_count.get() + 1);
            n * n
        });

        cacher.value(3);
        cacher.value(3);

        assert_eq!(1, call_count.get());
    }

    #[test]
    fn test_different_args_cached_separately() {
        let call_count = Cell::new(0);
        let mut cacher = Cacher::new(|n| {
            call_count.set(call_count.get() + 1);
            n + 1
        });

        assert_eq!(2, cacher.value(1));
        assert_eq!(6, cacher.value(5));
        assert_eq!(2, call_count.get());

        cacher.value(1);
        cacher.value(5);

        assert_eq!(2, call_count.get());
    }

    #[test]
    fn test_zero_input() {
        let mut cacher = Cacher::new(|n| n * n);
        assert_eq!(0, cacher.value(0));
    }
}
