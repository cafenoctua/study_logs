// //! # My Crate
// //!
// //! `my_crate` is a collection of utilities to make performing certain
// //! calculations more convenient.  

// /// Adds one to the number given.
// /// 
// /// # Example
// /// 
// /// ```
// /// let five = 5;
// /// 
// /// assert_eq!(6, my_crate::add_one(5));
// /// ```
// pub fn add_one(x: i32) -> i32 {
//     x + 1
// }

//! # Art
//! 
//! A library for modeling artistic concepts.

pub use kinds::PrimaryColor;
pub use kinds::SecondaryColor;
pub use utils::mix;

pub mod kinds {
    /// The primary colors according to the RYB color model.
    pub enum PrimaryColor {
        Red,
        Yellow,
        Blue,
    }

    /// The secondary colors according to the RYB color model.
    pub enum SecondaryColor {
        Orange,
        Green,
        Purple,
    }
}

pub mod utils {
    use crate::kinds::{PrimaryColor, SecondaryColor};

    /// Combines two primary colors in equal amounts to create
    /// a secondary color.
    pub fn mix(ci: PrimaryColor, c2: PrimaryColor) {
        //
    }
}