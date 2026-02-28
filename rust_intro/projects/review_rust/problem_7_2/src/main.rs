use std::sync::mpsc;
use std::thread;
use std::time::Duration;

fn main() {
    // TODO: 実装
    // 1. 3つのプロデューサースレッドを作成
    let (tx, rx) = mpsc::channel();
    let mut children = Vec::new();

    for id in 0..3 {
        let thread_tx = tx.clone();

        let child = thread::spawn(move || {
            // 2. 各プロデューサーは自分のIDと1〜5の数字を送信
            for i in 1..=5 {
                let message = format!("スレッド{}: {}", id, i);
                thread_tx.send(message).unwrap();

                thread::sleep(Duration::from_millis(100));
            }
        });

        children.push(child);
    }

    drop(tx);

    // 3. メインスレッドで全メッセージを受信して表示
    for received in rx {
        println!("{:?}", received);
    }

    for child in children {
        child.join().unwrap();
    }
}
