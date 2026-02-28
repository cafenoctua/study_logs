#[derive(Debug)]
struct Rectangle {
    // TODO: フィールドを定義
    width: u32,
    height: u32,
}

impl Rectangle {
    fn new(width: u32, height: u32) -> Self {
        // TODO: 実装
        Self {
            width: width,
            height: height,
        }
    }

    fn area(&self) -> u32 {
        // TODO: 実装
        self.width * self.height
    }

    fn perimeter(&self) -> u32 {
        // TODO: 実装
        if self.width == 0 || self.height == 0 {
            return 0;
        };

        (self.width + self.height) * 2
    }

    fn is_square(&self) -> bool {
        // TODO: 実装
        if self.width == 0 || self.height == 0 {
            return false;
        }

        self.width == self.height
    }
}

fn main() {
    let rect = Rectangle::new(10, 20);
    println!("長方形: {:?}", rect);
    println!("面積: {}", rect.area());
    println!("周囲長: {}", rect.perimeter());
    println!("正方形か: {}", rect.is_square());
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn calc_square() {
        let rect = Rectangle::new(2, 2);
        assert_eq!(4, rect.area());
        assert_eq!(8, rect.perimeter());
        assert_eq!(true, rect.is_square());
    }

    #[test]
    fn return_0() {
        let rect = Rectangle::new(0, 0);
        assert_eq!(0, rect.area());
        assert_eq!(0, rect.perimeter());
        assert_eq!(false, rect.is_square());
    }

    #[test]
    fn width_0() {
        let rect = Rectangle::new(0, 2);
        assert_eq!(0, rect.area());
        assert_eq!(0, rect.perimeter());
        assert_eq!(false, rect.is_square());
    }
}
