use std::io;
use std::cmp::Ordering;

fn main() {
    println!("Guess the number!");  // 数を当ててごらん

    let secret_number = rand::random_range(1..101);

    loop {

        println!("Please input your guess.");  // ほら、予想を入力してね

        let mut guess = String::new();

        io::stdin()
            .read_line(&mut guess)
            .expect("Failed to read line");

        let guess: u32 = match guess.trim().parse() {
            Ok(num) => num,
            Err(_) => continue,
        };

        println!("You guessed: {}", guess);  // 君の予想は{guess}だね

        match guess.cmp(&secret_number) {
            Ordering::Less => println!("Too small!"),
            Ordering::Greater => println!("Too big!"),
            Ordering::Equal => {
                println!("You win!");
                break;
            }
        }
    }
}
