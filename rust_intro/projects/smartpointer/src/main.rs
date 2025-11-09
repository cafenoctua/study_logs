#[derive(Debug)]

enum List {
    Cons(Rc<RefCell<i32>>, Rc<List>),
    Nil,
}

enum ListCycle {
    ConsCycle(i32, RefCell<Rc<ListCycle>>),
    NilCycle,
}

impl ListCycle {
    fn tail(&self) -> Option<&RefCell<<Rc<ListCycle>>> {
        match *self {
            ConsCycle(_, ref item) => Some(item),
            NilCycle => None,
        }
    }
}

use List::{Cons, Nil};
use ListCycle::{ConsCycle, NilCycle};

struct MyBox<T>(T);

impl<T> MyBox<T> {
    fn new(x: T) -> MyBox<T> {
        MyBox(x) 
    }
}

use std::cell::RefCell;
use std::{self, ops::Deref};
impl<T> Deref for MyBox<T> {
    type Target = T;

    fn deref(&self) -> &T {
        &self.0
    }
}

fn hello(name: &str) { 
    println!("Hello, {}!", name);
}

struct CustomSmartPointer {
    data: String,
}

impl Drop for CustomSmartPointer {
    fn drop(&mut self) {
        println!("Dropping CustomSmartPointer with data `{}`!", self.data);
    }
}

use std::rc::Rc;

fn main() {
    let b = Box::new(5);
    println!("b = {}", b);

    // let list = Cons(1,
    //     Box::new(Cons(2,
    //         Box::new(Cons(3,
    //             Box::new(Nil))))));
    
    let x = 5;
    let y = &x;

    assert_eq!(5, x);
    assert_eq!(5, *y);

    let x = 5;
    let y = Box::new(x);

    assert_eq!(5, x);
    assert_eq!(5, *y);

    let x = 5;
    let y = MyBox::new(x);

    assert_eq!(5, x);
    assert_eq!(5, *y);

    let m = MyBox::new(String::from("Rust"));
    hello(&(*m)[..1]);

    let c = CustomSmartPointer { data: String::from("my stuff") };
    let d = CustomSmartPointer { data: String::from("other stuff") };

    println!("CustomSmartPointers created.");

    let c = CustomSmartPointer { data: String::from("some data") };
    println!("CustomSmartPointer created.");
    drop(c);
    println!("CustomSmartPointer dropped before the end of main.");

    // let a = Rc::new(Cons(5, Rc::new(Cons(10, Rc::new(Nil)))));
    // let b = Cons(3, Rc::clone(&a));
    // let c = Cons(4, Rc::clone(&a));

    // let a = Rc::new(Cons(5, Rc::new(Cons(10, Rc::new(Nil)))));
    // println!("count after creating a = {}", Rc::strong_count(&a));
    // let b = Cons(3, Rc::clone(&a));
    // println!("count after creating b = {}", Rc::strong_count(&a));
    // {
    //     let c = Cons(4, Rc::clone(&a));
    //     println!("count after creating c = {}", Rc::strong_count(&a));
    // }
    // println!("count after c goes out of scope = {}", Rc::strong_count(&a));

    let value = Rc::new(RefCell::new(5));

    let a = Rc::new(ConsCycle(Rc::clone(&value), Rc::new(NilCycle)));

    let b = Cons(Rc::new(RefCell::new(6)), Rc::clone(&a));
    let c = Cons(Rc::new(RefCell::new(10)), Rc::clone(&a));

    *value.borrow_mut() += 10;

    println!("a after = {:?}", a);
    println!("b after = {:?}", b);
    println!("c after = {:?}", c);

    let a = Rc::new(ConsCycle(5, RefCell::new(NilCycle)));

    println!("a next item = {:?}", Rc::strong_count(&a));
    println!("a next item = {:?}", a.tail());

    let b = Rc::new(ConsCycle(10, RefCell::new(Rc::clone(&a))));

    println!("a rc count after  creation = {}", Rc::strong_count(&a));
    println!("b initial rc count = {}", Rc::strong_count(&b));
    println!("b next item = {:?}", b.tail());

    if let Some(link) = a.tail() {
        *link.borrow_mut() = Rc::strong_count(&b);
    }

    println!("b rc count after changing a = {}", Rc::strong_count(&b));
    println!("a rc count after changing a = {}", Rc::strong_count(&a));

}
