use std::{fs::File, io::{ErrorKind, Read}, net::IpAddr};
use std::io;

fn main() {
    // panic!("crash and burn");
    let v = vec![1, 2, 3];

    // インデックスのアクセスエラー
    // v[99];

    let f = File::open("hello1.txt");

    let f = match f {
        Ok(file) => file,
        Err(ref error) if error.kind() == ErrorKind::NotFound => {
            match File::create("hello1.txt") {
                Ok(fc) => fc,
                Err(e) => {
                    panic!(
                        "Tried to create file but there was a problem: {:?}",
                        e
                    )
                },
            }
        },
        Err(error) => {
            panic!(
                "There was a problem opening the file: {:?}",
                error
            )
        },
    };

    // let f = File::open("hello1.txt").unwrap();
    // let f = File::open("hello2.txt").expect("Failed to open hello2.txt");

    let f = read_username_from_file();
    let f = match f {
        Ok(file) => file,
        Err(error) => {
            panic!(
                "There was a problem opening the file: {:?}",
                error
            )
        },   
    };

    let f = read_username_from_file_p2();
    let f = match f {
        Ok(file) => file,
        Err(error) => {
            panic!(
                "There was a problem opening the file: {:?}",
                error
            )
        },   
    };

    let f = read_username_from_file_p3();
    let f = match f {
        Ok(file) => file,
        Err(error) => {
            panic!(
                "There was a problem opening the file: {:?}",
                error
            )
        },   
    };

    // Result型で返すことが定義されていないためエラーになる
    // let f = File::open("hello.txt")?;

    let home: IpAddr = "127.0.0.1".parse().unwrap();

    guess_number();

}


fn read_username_from_file() -> Result<String, io::Error> {
    let f = File::open("hello1.txt");
    let mut f = match f {
        Ok(file) => file,
        Err(e) => return Err(e),
    };
    let mut s = String::new();
    match f.read_to_string(&mut s) {
        Ok(_) => Ok(s),
        Err(e) => Err(e),
    }
}

fn read_username_from_file_p2() -> Result<String, io::Error> {
    let mut f = File::open("hello.txt")?;
    let mut s = String::new();
    f.read_to_string(&mut s)?;
    Ok(s)
}

fn read_username_from_file_p3() -> Result<String, io::Error> {
    let mut s = String::new();
    
    File::open("hello.txt")?.read_to_string(&mut s)?;
    
    Ok(s)
}

use std::cmp::Ordering;

pub struct Guess {
    value: u32,
}

impl Guess {
    pub fn new(value: u32) -> Guess {
        if value < 1 || value > 100 {
            panic!("Guess value must be between 1 and 100, got {}.", value);
        }

        Guess { value }
    }

    pub fn value(&self) -> u32 {
        self.value
    }
}

fn guess_number() {
    println!("Guess the number!");  // 数を当ててごらん

    let secret_number = rand::random_range(1..101);

    loop {

        println!("Please input your guess.");  // ほら、予想を入力してね

        let mut guess = String::new();

        io::stdin()
            .read_line(&mut guess)
            .expect("Failed to read line");

        let guess: Guess = Guess::new(match guess.trim().parse() {
            Ok(num) => num,
            Err(_) => continue,
        });
        
        let guess_num = guess.value();
        println!("You guessed: {}", guess_num);  // 君の予想は{guess}だね

        match guess_num.cmp(&secret_number) {
            Ordering::Less => println!("Too small!"),
            Ordering::Greater => println!("Too big!"),
            Ordering::Equal => {
                println!("You win!");
                break;
            }
        }
    }
}
