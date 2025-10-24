// use core::num;
// use std::intrinsics::{powf64, powif64};

fn main() {

    // if condition codes
    let number = 7;

    if number < 5 {
        println!("condition was true!")
    } else {
        println!("condition was false")
    }

    if number != 0 {
        println!("number was something other than zero");
    }

    if number % 4 == 0 {
        println!("number is divisible by 4");
    } else if number % 3 == 0 {
        println!("number is divisible by 3");
    } else if number % 2 == 0 {
        println!("number is divisible by 2");
    } else {
        println!("number is not divisible by 4, 3 or 2");
    }

    let condition = true;
    let number = if condition { 5 } else { 6 };

    println!("The value of number is: {}", number);

    // // error code
    // let condition = true;
    // let number = if condition { 5 } else { "six" };

    // println!("The value of number is: {}", number);

    // loop codes

    let mut count = 0;
    'counting_up: loop {
        println!("count = {}", count);
        let mut remaining = 10;

        loop {
            println!("remaining = {}", remaining);
            if remaining == 9 {
                break;
            }
            if count == 2 {
                break 'counting_up;
            }
            remaining -= 1;
        }
        count += 1 ;
    }
    println!("End count = {}", count);

    let mut number = 3;

    while number != 0 {
        println!("{}!", number);

        number -= 1;
    }

    println!("LIFTOFF!");

    let a = [10, 20, 30, 40, 50];
    let mut index = 0;

    while index < 5 {
        println!("the value is: {}", a[index]);

        index += 1;
    }

    for element in a {
        println!("the value is; {}", element);
    }

    for number in (1..4).rev() {
        println!("{}!", number);
    }
    println!("LIFTOFF!!!!");

    println!("Conversion to Fahrenheit: {}", conv_temp_to_fahr(10.0));

    println!("Output N fibo: {}", fibonacci_exp(10.0))
}


fn conv_temp_to_fahr (temp: f64) -> f64 {
    (temp * 9.0 / 5.0) + 32.0
}

fn fibonacci_exp(n: f64) -> f64{
    // const P: f64 = 10_f64.powf(9) + 7.0;
    if n <= 1.0 {
        return n;
    }

    return (fibonacci_exp(n-1.0)+fibonacci_exp(n-2.0));
    
}