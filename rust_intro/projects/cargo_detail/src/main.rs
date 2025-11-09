extern crate cargo_detail;
use cargo_detail::kinds::PrimaryColor;
use cargo_detail::utils::mix;
fn main() {
    let red = PrimaryColor::Red;
    let yellow = PrimaryColor::Yellow;
    mix(red, yellow);
}