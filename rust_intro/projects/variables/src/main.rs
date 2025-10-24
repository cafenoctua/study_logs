use std::io;

fn main() {
    let mut x = 5;
    println!("The value of x is: {}", x);
    x = 6;
    println!("The value of x is: {}", x);

    const MAX_POINTS: u32 = 100_000;

    let x = 5;

    let x= x + 1;
    {
        let x = x * 2;
        println!("The values of x in the inner scope is : {}", x);
    }
    println!("The values of x is : {}", x);

    let spaces = "      ";
    let spaces = spaces.len();

    let mut spaces = "      ";
    // 別データ型での再代入によりエラー発生
    // spaces = spaces.len();

    let guess: u32 = "42".parse().expect("Not a number!");

    // let guess: u32 = "42".parse().expect("Not a number!");
    println!("{}", guess);

    let tup: (i32, f64, u8) = (500, 6.4, 1);

    let (x, y, z) = tup;
    println!("The value of y is: {}", y);

    let x: (i32, f64, u8) = (500, 6.4, 1);

    let _five_hundred = x.0;

    let _six_point_four = x.1;

    let _one = x.2;

    
    let a = [3; 5];
    println!("{}", a[1]);

    let a = [1,2,3,4,5];

    println!("Please enter an array index.");

    let mut index = String::new();

    io::stdin()
        .read_line(&mut index)
        .expect("Failed to read line");

    let index: usize = index
        .trim()
        .parse()
        .expect("Index entered was not a number");

    let element = a[index];

    println!(
        "The values of the element at index {} is: {}",
        // P{罰mねの要素の値の{}です
        index, element
    )
}