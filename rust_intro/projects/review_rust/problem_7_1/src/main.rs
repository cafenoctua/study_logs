use std::sync::{Arc, Mutex};
use std::thread;

fn parallel_sum(numbers: Vec<i32>, num_threads: usize) -> i32 {
    // TODO: 実装
    // ヒント: Arc<Mutex<i32>>で共有状態を管理

    let sum = Arc::new(Mutex::new(0));

    let data = Arc::new(numbers);

    let mut handles = vec![];

    for thread_id in 0..num_threads {
        let sum_clone = Arc::clone(&sum);
        let data_clone = Arc::clone(&data);

        let handle = thread::spawn(move || {
            let chunk_size = data_clone.len() / num_threads;

            let start = thread_id * chunk_size;
            let end = if thread_id == num_threads - 1 {
                data_clone.len()
            } else {
                (thread_id + 1) * chunk_size
            };

            let mut local_sum = 0;
            for i in start..end {
                local_sum += data_clone[i];
            }

            let mut global_sum = sum_clone.lock().unwrap();
            *global_sum += local_sum;
        });

        handles.push(handle);
    }

    for handle in handles {
        handle.join().unwrap();
    }

    let result = sum.lock().unwrap();
    *result
}

fn main() {
    let numbers: Vec<i32> = (1..=100).collect();
    let result = parallel_sum(numbers, 4);
    println!("合計: {}", result); // 5050
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_sum() {
        // 1から100までの合計 = 5050
        let numbers: Vec<i32> = (1..=100).collect();
        let result = parallel_sum(numbers, 4);
        assert_eq!(5050, result);
    }

    #[test]
    fn test_small_data_many_threads() {
        // データが少なくスレッド数が多い場合
        let numbers = vec![1, 2, 3, 4];
        let result = parallel_sum(numbers, 4);
        assert_eq!(10, result);
    }

    #[test]
    fn test_single_thread() {
        // 1スレッドの場合（逐次処理と同じ）
        let numbers: Vec<i32> = (1..=10).collect();
        let result = parallel_sum(numbers, 1);
        assert_eq!(55, result);
    }

    #[test]
    fn test_two_threads() {
        // 2スレッドの場合
        let numbers = vec![10, 20, 30, 40];
        let result = parallel_sum(numbers, 2);
        assert_eq!(100, result);
    }

    #[test]
    fn test_empty_vector() {
        // 空のベクター
        let numbers: Vec<i32> = vec![];
        let result = parallel_sum(numbers, 4);
        assert_eq!(0, result);
    }

    #[test]
    fn test_negative_numbers() {
        // 負の数を含む場合
        let numbers = vec![-5, -3, 0, 3, 5];
        let result = parallel_sum(numbers, 2);
        assert_eq!(0, result);
    }

    #[test]
    fn test_large_thread_count() {
        // スレッド数がデータ数より多い場合
        let numbers = vec![1, 2, 3];
        let result = parallel_sum(numbers, 10);
        assert_eq!(6, result);
    }

    #[test]
    fn test_odd_number_elements() {
        // 奇数個の要素を均等に分割
        let numbers = vec![1, 2, 3, 4, 5, 6, 7];
        let result = parallel_sum(numbers, 3);
        assert_eq!(28, result);
    }
}
