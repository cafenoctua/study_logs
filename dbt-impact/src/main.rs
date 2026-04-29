mod manifest;
use std::path::Path;

use manifest::Manifest;

fn main() {
    let path = Path::new("manifest.json");
    let manifest = Manifest::load(path);
    print!("{:?}", manifest.unwrap().nodes.len());
}
