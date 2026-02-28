// ヒント: 華氏 = 摂氏 * 9/5 + 32

fn celsius_to_fahrenheit(celsius: f64) -> f64 {
    // TODO: 実装してください
    celsius * 1.8 + 32.0
}

fn fahrenheit_to_celsius(fahrenheit: f64) -> f64 {
    // TODO: 実装してください
    (fahrenheit - 32.0) * (5.0 / 9.0)
}

fn main() {
    let c = 25.0;
    println!("{:.1}°C = {:.1}°F", c, celsius_to_fahrenheit(c));

    let f = 77.0;
    println!("{:.1}°F = {:.1}°C", f, fahrenheit_to_celsius(f));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn freezing_point() {
        assert_eq!(32.0, celsius_to_fahrenheit(0.0))
    }

    #[test]
    fn boiling_point() {
        assert_eq!(212.0, celsius_to_fahrenheit(100.0))
    }

    #[test]
    fn minus_celsius() {
        assert_eq!(30.2, celsius_to_fahrenheit(-1.0))
    }

    #[test]
    fn minus_fahrenheit() {
        assert_eq!(-18.333333333333336, fahrenheit_to_celsius(-1.0))
    }
}
