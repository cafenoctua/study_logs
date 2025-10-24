use std::{collections::HashMap, hash::Hash};

fn main() {
    let v: Vec<i32> = Vec::new();
    
    let mut v = Vec::new();
    
    v.push(5);
    v.push(6);
    v.push(7);
    v.push(8);

    let v = vec![1, 2, 3, 4];
    drop(v);

    let v = vec![1, 2, 3, 4, 5];

    let third: &i32 = &v[2];
    println!("The third element is {}", third);

    match v.get(2) {
        Some(third) => println!("The third element is {}", third),
        None => println!("There is no third element."),
    }

    // let does_not_exist = &v[100];
    // let does_not_exist = v.get(100);

    let mut v = vec![1, 2, 3, 4, 5];

    let first = &v[0];

    // v.push(6);

    println!("The first element is: {}", first);

    let mut v = vec![100, 32, 57];
    for i in &mut v {
        *i += 50;
        println!("{}", i);
    }

    enum SpreadsheetCell {
        Int(i32),
        Float(f64),
        Text(String),
    }

    let row = vec![
        SpreadsheetCell::Int(3),
        SpreadsheetCell::Text(String::from("blue")),
        SpreadsheetCell::Float(10.12),
    ];

    let mut s = String::new();

    let data = "initial contents";
    let s = data.to_string();

    let s = "initial contens".to_string();
    
    // let s = "initial contens".to_string();と等価になる
    let s = String::from("initial contens");

    // 有効なString型
    let hello = String::from("Hello");
    let hello = String::from("こんにちは");

    let mut s = String::from("foo");
    s.push_str("bar");

    let mut s1 = String::from("foo");
    let s2 = "bar";
    s.push_str(s2);
    println!("s2 is {}", s2);

    let mut s = String::from("lo");
    s.push('l');

    println!("{}", s);

    let s1 = String::from("Hello, ");
    let s2 = String::from("world!");
    let s3 = s1 + &s2;
    println!("{}", s3);

    let s1 = String::from("tic");
    let s2 = String::from("tac");
    let s3 = String::from("toe");

    let s =format!("{}-{}-{}", s1, s2, s3);
    println!("{}", s);

    // インデックスアクセスによるエラーコード
    // let s1 = String::from("hello!");
    // let h = s1[0];

    // 1バイト文字列
    println!("{}", String::from("Hola").len());
    // 2バイト文字列
    println!("{}", String::from("Здравствуйте").len());

    let  hello = "Здравствуйте";
    // インデックスアクセスによるエラー
    // let answer = &hello[0];
    let s = &hello[0..4];
    println!("{}", s);

    for c in "Здравствуйте".chars() {
        println!("{}", c);
    }

    for b in "Здравствуйте".bytes() {
        println!("{}", b);
    }

    let mut scores = HashMap::new();
    scores.insert(String::from("Blue"), 10);
    scores.insert(String::from("Yellow"), 50);

    let teams = vec![String::from("Blue"), String::from("Yellow")];
    let initial_scores = vec![10, 50];

    let scores: HashMap<_, _> = teams.iter().zip(initial_scores.iter()).collect();

    let field_name = String::from("Favorite color");
    let field_value = String::from("Blue");

    let mut map = HashMap::new();
    map.insert(field_name, field_value);

    let mut scores = HashMap::new();

    scores.insert(String::from(("Blue")),10);
    scores.insert(String::from("Yellow"), 50);

    let team_name = String::from("Blue");
    let score = scores.get(&team_name);
    for (key, value) in &scores {
        println!("{}: {}", key, value);
    }

    let mut scores = HashMap::new();

    scores.insert(String::from("Blue"), 10);
    scores.insert(String::from("Blue"), 25);

    scores.entry(String::from("Yellow")).or_insert(50);
    // キーが既出のため上書きされない
    scores.entry(String::from("Blue")).or_insert(50);

    println!("{:#?}", scores);

    let text = "hello world wonderful world";

    let mut map = HashMap::new();

    for word in text.split_whitespace() {
        let count = map.entry(word).or_insert(0);
        *count += 1;
    }

    println!("{:?}", map);

    let value_list = vec![10, 20, 35, 35, 40, 50];

    // mean
    let total: u32 = value_list.iter().sum();
    let len: u32 = value_list.iter().count() as u32;
    println!("mean: {}", total / len);

    // median
    let a = (len / 2) as usize;
    println!("media: {}", value_list[a]);

    // mode
    let mut map = HashMap::new();
    for v in value_list.iter() {
        let count = map.entry(v).or_insert(0);
        *count += 1;
    }

    let max_count = map.values().max();
    
    for (key, value) in &map {
        if Some(value) == max_count {
            println!("mode: {}", key);
            break;
        }
    }

    // big laten
    let a = String::from("aiueo");
    let text = String::from("first");
    // let text = String::from("apple");

    let mut biglaten_flg = false;
    for c in a.chars() {
        if String::from(c) == text[0..1] {
            let text_concat = format!("{}-hay", &text[..]);
            println!("{}", text_concat);
            biglaten_flg = true;
        }
    }

    if biglaten_flg == false {
        let text_concat = format!("{}-{}ay", &text[1..], &text[..1]);
        println!("{}", text_concat);
    }

}
