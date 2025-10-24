struct Ipv4Addr {
    ip_format: (u8, u8, u8, u8)
}

struct Ipv6Addr {
    ip_format: String
}

enum IpAddrKind {
    V4(Ipv4Addr),
    V6(Ipv6Addr)
}

struct IpAddr {
    kind: IpAddrKind,
    address: String,
}

struct QuitMessage;
struct MoveMessage {
    x: i32,
    y: i32,
}
struct writeMessage(String);
struct ChangeColoerMessage(i32, i32, i32);

#[derive(Debug)]
enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
    ChangeColoer(i32, i32, i32),
}

impl Message {
    fn call(&self) {
        println!("Message {:#?}", &self)
    }
}

enum Option<T> {
    Some(T),
    None
}

fn main() {
    // let home = IpAddr {
    //     kind: IpAddrKind::V4,
    //     address: String::from("127.0.0.1"),
    // };

    // let loopback = IpAddr {
    //     kind: IpAddrKind::V6,
    //     address: String::from("::1"),
    // };

    // let home = IpAddrKind::V4{ ip_format: (127, 0, 0, 1) };
    // let loopback = IpAddrKind::V6(String::from("::1"));

    let m = Message::Write(String::from("hello"));
    m.call();

    // let some_number = Some(5);
    // let some_string = Some("a string");

    // let absent_number: Option<i32> = None;

    // let x: i8 = 5;
    // let y: Option<i8> = Some(5);
    
    // calcuration data type missmatch.
    // let sum = x + y;
}