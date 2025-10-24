#[derive(Debug)]
struct Rectangle {
    width: u32,
    height: u32
}

fn main() {
    let user = User {
        email: String::from("someone@example.com"),
        username: String::from("someusername123"),
        active: true,
        sign_in_count: 1,
    };

    println!("user info: {}", user.email);
    
    let mut user1 = User {
        email: String::from("someone@example.com"),
        username: String::from("someusername123"),
        active: true,
        sign_in_count: 1,
    };
    
    user1.email = String::from("anotheremail@ezample.com");
    println!("user info: {}", user1.email);

    let user1 = build_user(String::from("sameone@example.com"), String::from("someusername123"));

    let user2 = User {
        email: String::from("another@example.com"),
        username: String::from("anotherusername567"),
        ..user
    };

    struct Color(i32, i32, i32);
    struct Point(i32, i32, i32);

    let black = Color(0, 0, 0);
    let origin = Point(0, 0, 0);

    // let user1 = User1 {
    //     email: "someone@example.com",
    //     username: "someusername123",
    //     active: true,
    //     sign_in_count: 1,
    // };

    // let width1 = 30;
    // let height1 = 50;

    // let rect1 = (30, 50);

    let rect1 = Rectangle {width: 30, height: 50};

    println!("rect1 is {:?}", rect1);

    println!("rect1 is {:#?}", rect1);

    println!(
        "The area of the rectangle is {} square pixels.",
        area(&rect1)
    );
}

struct User {
    username: String,
    email: String,
    sign_in_count: u64,
    active: bool
}

// ライフタイムが明示されないためエラーになる
// struct User1 {
//     username: &str,
//     email: &str,
//     sign_in_count: u64,
//     active: bool
// }

fn build_user(email: String, username: String) -> User {
    User {
        email,
        username,
        active: true,
        sign_in_count: 1,
    }
}

fn area(rectable: &Rectangle) -> u32 {
    rectable.width * rectable.height
}