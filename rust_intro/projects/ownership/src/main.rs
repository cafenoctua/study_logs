fn main() {
    let s1 = String::from("hello");
    let s2 = s1.clone();

    println!("s1 = {}, s2 = {}", s1, s2);

    let x = 5;
    let y = x;
    println!("x = {}, y = {}", x, y);

    let s = String::from("hello");

    takes_ownership(s);
    // println!("{}", s);

    let x = 5;

    makes_copy(x);

    println!("{}", x);

    let s1 = gives_ownership();

    let s2 = String::from("hello");

    let s3 = takes_and_gives_back(s2);

    let s1 = String::from("hello");
    
    let (s2, len) = calculate_length(s1);


    println!("The length of '{}' is {}.", s2, len);
    
    let s1 = String::from("hello");
    let len = calculate_length_ref(&s1);
    println!("The length of '{}' is {}.", s1, len);

    let mut s = String::from("hello");

    //　エラーコード
    // let r1 = &mut s;
    // let r2 = &mut s;

    // println!("{}, {}", r1, r2);

    // change(&s);

    let reference_to_nothing = dangle();

    let mut s = String::from("hello world there");
    
    let word1 = first_word(&s);
    // 文字列スライスにより参照が続きclear後に文字列スライス型の変数にアクセスするとエラーになる
    // s.clear();
    println!("word1 = {}", word1);

    let word2 = second_word(&s);
    println!("word2 = {}", word2);

    let hello = &s[0..5];
    let world = &s[6..11];

    let my_string = String::from("hello world");

    let word = first_word(&my_string[..]);

    let my_string_literal = "hello world";

    let word = first_word(&my_string_literal[..]);

    let word = first_word(my_string_literal);

    let a = [1, 2, 3, 4, 5];

    let slice = &a[1..3];

}

fn takes_ownership(some_string: String) {
    println!("{}", some_string);
}

fn makes_copy(some_integer: i32) {
    println!("{}", some_integer)
}

fn gives_ownership() -> String {
    let some_string = String::from("hello");
    some_string
}

fn takes_and_gives_back(a_string: String) -> String {
    a_string
}

fn calculate_length(s: String) -> (String, usize) {
    let length = s.len();

    (s, length)
}

fn calculate_length_ref(s: &String) -> usize {
    s.len()
}

fn change(some_string: &mut String) {
    some_string.push_str(", world");
}

fn dangle() -> String {
    let s = String::from("hello");

    s
}

fn first_word(s: &str) -> &str {
    let bytes = s.as_bytes();

    for (i, &item) in bytes.iter().enumerate() {
        if item == b' ' {
            return &s[0..i];
        }
    }

    &s[..]
}

fn second_word(s: &String) -> &str {
    let bytes = s.as_bytes();
    
    let mut cnt = 0;
    let mut start_pos = 0;
    let mut end_pos = 100000000;
    for (i, &item) in bytes.iter().enumerate() {
        if item == b' ' {
            cnt += 1;
            if cnt == 1 {
                start_pos = i + 1;
            }
            if cnt == 2 {
                end_pos = i;
            }
        }
    }

    &s[start_pos..end_pos]
}