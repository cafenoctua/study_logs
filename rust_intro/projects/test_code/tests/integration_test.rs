extern crate test_code;
mod common;

#[test]
fn it_adds_two() {
    common::setup();
    assert_eq!(4, test_code::add_two(2));
}