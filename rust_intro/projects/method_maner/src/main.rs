#[derive(Debug)]
struct Rectangle {
    width: u32,
    heigth: u32,
}

impl Rectangle {
    fn area(&self) -> u32 {
        self.width * self.heigth
    }

    fn can_hols(&self, other: &Rectangle) -> bool {
        self.width > other.width && self.heigth > other.heigth
    }
}

impl Rectangle {
    fn square(size: u32) -> Rectangle {
        Rectangle { width:size, heigth: size }
    }
}

fn main() {
    let rect1 = Rectangle { width: 30, heigth: 50 };
    let rect2 = Rectangle { width: 10, heigth: 40 };
    let rect3 = Rectangle { width: 60, heigth: 45 };

    println!("Can rect1 hold rect2? {}", rect1.can_hols(&rect2));
    println!("Can rect1 hold rect3? {}", rect1.can_hols(&rect3));

    let sq = Rectangle::square(3);

    println!("Squre size: {:#?}", sq);
}
