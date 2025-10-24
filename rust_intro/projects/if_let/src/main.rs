fn main() {
    let some_u8_value = Some(3u8);

    match some_u8_value {
        Some(3) => println!("there"),
        _ => (),
    }

    if let Some(3) = some_u8_value {
        print!("three");
    }
}
