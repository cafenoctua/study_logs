use std::sync::{mpsc, Arc, Mutex};
use std::thread;

use num_traits::pow;

fn parallel_pow(num_threads: i32, tasks: Vec<i32>) -> Vec<(i32, i32)> {
    // 1. タスクチャネル: メインスレッド → ワーカーへタスクを送る
    let (tx, rx) = mpsc::channel::<i32>();
    let rx = Arc::new(Mutex::new(rx)); // 複数ワーカーで共有するためArc<Mutex>で包む

    // 2. 結果チャネル: ワーカー → メインスレッドへ結果を返す
    let (result_tx, result_rx) = mpsc::channel::<(i32, i32)>(); // (元の値, 結果)

    // 3. ワーカースレッドを起動
    let mut handles = vec![];
    for worker_id in 0..num_threads {
        let rx_clone = Arc::clone(&rx);
        let result_tx_clone = result_tx.clone();

        let handle = thread::spawn(move || {
            // TODO(human): ワーカーのタスク処理ループを実装してください
            // rx_clone から Mutex をロックしてタスク(数値)を受信し、
            // 2乗を計算して result_tx_clone で (元の値, 結果) を送信する
            // チャネルが閉じたらループを抜ける
            //
            // ヒント:
            //   let task = rx_clone.lock().unwrap().recv();
            //   match task { Ok(n) => ..., Err(_) => break }
            loop {
                let task = rx_clone.lock().unwrap().recv();
                match task {
                    Ok(n) => {
                        println!("Worker {} が {} を処理", worker_id, n);
                        result_tx_clone.send((n, pow(n, 2))).unwrap()
                    }
                    Err(_) => break,
                }
            }
        });
        handles.push(handle);
    }

    // 4. タスク投入: 1〜10の数値をキューに送信
    for n in tasks {
        tx.send(n).unwrap();
    }

    drop(tx); // 送信側を閉じてワーカーのループが終了するようにする

    drop(result_tx); // メインスレッド側のクローンも閉じる

    for handle in handles {
        handle.join().unwrap();
    }
    // 5. 結果を収集
    let mut results: Vec<(i32, i32)> = vec![];
    for result in result_rx {
        results.push(result);
    }

    // ソートして表示（スレッドの実行順は不定なため）
    results.sort_by_key(|&(n, _)| n);
    results
}

fn main() {
    let num_threads = 3;
    let tasks = (1..=10).collect();

    let results = parallel_pow(num_threads, tasks);
    for (n, squared) in &results {
        println!("{}^2 = {}", n, squared);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_single_thread_return_1() {
        let results = parallel_pow(1, vec![1]);

        assert_eq!(vec![(1, 1)], results);
    }
}
