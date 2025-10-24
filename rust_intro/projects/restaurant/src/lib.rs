use std::collections::HashMap;
use std::fmt;
// use std::io;
use std::io::Result as IoResult;
use rand::random;
use rand::Rng;
use std::{cmp::Ordering}; //}, io};
use std::io::{self, Write};
use std::collections::*;

// mod front_of_house {
//     pub mod hosting {
//         pub fn add_to_waitlist() {}

//         fn seat_at_table() {}
//     }

//     mod serving {
//         fn take_order () {}

//         fn serve_order() {}

//         fn take_payment () {}
//     }
// }

mod front_of_house;
use crate::front_of_house::hosting;
// use self::front_of_house::hosting;

use crate::front_of_house::hosting::add_to_waitlist;

fn serve_order() {}

mod back_of_house {
    fn fix_incorrect_order() {
        cook_order();
        super::serve_order();
    }

    pub struct Breakfast {
        pub toast: String,
        seasonal_fruit: String,
    }
    impl Breakfast {
        pub fn summer(toast: &str) -> Breakfast {
            Breakfast { 
                toast: String::from(toast),
                seasonal_fruit: String::from("peaches"),
            }
        }
    }

    pub enum Appetizer {
        Soup,
        Salad
    }

    fn cook_order() {}
}

pub fn eat_at_restaurant() {
    // 絶対パス
    crate::front_of_house::hosting::add_to_waitlist();

    // 相対パス
    front_of_house::hosting::add_to_waitlist();

    let mut meal = back_of_house::Breakfast::summer("Rye");

    meal.toast = String::from("Wheat");
    println!("I'd like {} toast pleas", meal.toast);

    let order1 = back_of_house::Appetizer::Soup;
    let order2 = back_of_house::Appetizer::Salad;

    hosting::add_to_waitlist();
    hosting::add_to_waitlist();
    hosting::add_to_waitlist();

    add_to_waitlist();

    let mut map = HashMap::new();
    map.insert(1, 2);
}

// このように、fmt/ioでResult
// fn function1() -> fmt::Result {}
// fn function() -> io::Result<()> {}
// fn function3() -> IoResult<()> {}

fn main() {
    let secret_number = rand::thread_rng().gen_range(1..101);
}