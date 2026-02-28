# Rust

# getting start

- [x] https://www.rust-lang.org/learn/get-started
      環境構築とhello worldまでここでできる
- [x] [Rust入門書](https://doc.rust-jp.rs/book-ja/ch00-00-introduction.html)

# Cargo
## 役割
ビルドシステム兼パッケージマネージャ

## 使い方
プロジェクト作成
```
cargo new hello_cargo
```
これでプロジェクトに必要なディレクトリ、ファイルが作られる

## コマンド一覧
- `cargo new`を使ってプロジェクトを作成できる
- `cargo build`を使ってプロジェクトをビルドできる
	- `cargo build --release` を使うことでリリース用のバイナリをビルドできる(`release/` ディレクトリに格納される) 
- `cargo run`を使うとプロジェクトのビルドと実行を1ステップで行える
- `cargo check`を使うとバイナリを生成せずにプロジェクトをビルドして、エラーがないか確認できる
- Cargoは、ビルドの成果物をコードと同じディレクトリに保存するのではなく、_target/debug_ディレクトリに格納する

## TOML
uvと同じところあり
プロジェクトの最上位に置かれる

キー説明
- edition: 使用するRustのeditionを示す
- dependencies: プロジェクトの依存のリスト。ここで管理されるパッケージのことをRustでは、 `クレート` と呼ぶ
- 

## Build
デフォルトのビルドはデバッグビルドのためビルド後のバイナリはdebugディレクトリに置かれる

ビルドコマンドの実行
```
cargo build
```

release buildについて

```
cargo build --release
```
でrelease 向けのビルドが行われる
このビルドで最適化されたバイナリが生成されるためベンチマークの計測には、このバイナリを使う

## Run
コマンドの実行
```
cargo run
```

## Check
コマンドの実行
```
cargo check
```

コードのコンパイルが可能かチェックをすぐ行える

なぜ素早いか？
- buildステップを省略することができる

コード変更による継続的なコンパイルチェックはcheckコマンドがおすすめ

# 言語機能
## 標準入力
```rust
use std::io;
```
これで標準入力のライブラリを呼び出します

入力は以下のように設定することで入力を作れます
```rust
io::stdin()
	.read_line(&mut guess)
	.expect("Failed to read line");
```
## 例外処理
入力、実行など処理何かしらの処理にRustで必ず例外処理を設定することが推奨されます
## match式
>`match`式は複数の_アーム_（腕）で構成されます。 各アームはマッチさせる_パターン_と、`match`に与えられた値がそのアームのパターンにマッチしたときに実行されるコードで構成されます。 Rustは`match`に与えられた値を受け取って、各アームのパターンを順に照合していきます。 パターンと`match`式はRustの強力な機能で、コードか遭遇する可能性のあるさまざまな状況を表現し、それらすべてを確実に処理できるようにします。

以下のように作ることができます
```rust
match guess.cmp(&secret_number) {
    Ordering::Less => println!("Too small!"),
    Ordering::Greater => println!("Too big!"),
    Ordering::Equal => println!("You win!"),
}
```

# 所有権
所有権は、Rustのユニークな機能で、ガベージコレクションなしで安全性担保を行うことができる。

関連する機能
- 借用
- スライス

コンパイルがデータのメモリにどう配置するか注目

## とは？
Rustの中心的な機能。言語すべての機能に関わるコア機能。

全てのプログラムは、実行中にメモリの使用方法を管理する必要がある。
Rustのメモリ管理は、コンパイルはコンパイル時にチェックする一定の規則とともに所有権システムを通じて管理する。この機能によって実行中にプログラムの動作を遅くすることが無い。

## 活躍するところ
### ケース1(ヒープでのメモリクリーンアップ)
ヒープのメモリ領域から値が取り出されたときに、そこで未使用となったメモリ上のアドレスをクリーンアップします

## 所有権規則
- Rustの各値は、所有者と呼ばれる対応する変数がある
- 所有者はユニークである
- 所有者はスコー日外れたら、値が破棄される

## メモリの確保と解放
 Rustは、GCの代わりに変数がスコープから抜けたタイミングで所有権を返します = これがRustでのメモリの解放になる

メモリの解放が発生した(スコープから抜けた変数)にアクセスするとエラーになる

```rust
let s1 = String::from("hello");
let s2 = s1;

println!("s1 = {}, s2 = {}", s1, s2);
```

cloneメソッドを使うことで解決される
```rust
let s1 = String::from("hello");
let s2 = s1.clone();

println!("s1 = {}, s2 = {}", s1, s2);
```

その他エラーになるパターンとして、関数への変数渡しも該当する

```rust
fn main() {
    let s = String::from("hello");

    takes_ownership(s);
    println!("{}", s);
}

fn takes_ownership(some_string: String) {
    println!("{}", some_string);
}
```

では、全てのデータ型でそれが当てはまるか？

- リソースの予約が発生し、DROPトレイトを実装しているデータ型
  - 文字列リテラル
- リソースの予約が不要で、COPYトレイトを実装しているデータ型
  - 整数型
  - 論理値型
  - 浮動小数点型
  - 文字列型
  - タプル(ただし、上述している型で構成されている場合に限る)

## 参照と借用
`&` を使うことで関数の引数を参照型で定義できてデータの所有権が関数内部に渡さずに済む

![alt text](image.png)


書き方参考
```rust
fn calculate_length_ref(s: &String) -> usize {
    s.len()
}
```

可変参照渡しは、複数の変数で併用するとエラーになる。理由は、データ競合をコンパイル時点で防ぐため。

データ競合の条件
- 2つ以上のポイントが同じデータに同時にアクセスする場合
- 少なくとも一つがデータ書き込みを行っている
- データへのアクセスを同期する機構が備わっていない

データ競合は、実装して実行中に気づくとバグ取りが非常に厄介だけどRustは、そもそもコンパイルさせないことに優位性がある。

つまり、Rustは、ダングリングポインタの可能性あるコードはコンパイル時点でブロックする。

### 参照の規則
- 任意のタイミングで、単一の可変参照か複数の不変な参照が行える
- 参照は、常に有効である必要がある

### スライス型
所有権の無い参照型の一つ。スライスは、コレクション全体でなく、その内の一連の要素を参照するさせられる。

文字列スライスが作れ、安全に要素へのアクセスが可能で処理途中でメモリ解放した後にアクセスするようなバグを早期に検知する。

```rust
let hello = &s[0..5];
```

より、一般的なスライスもある。以下はリスト型をスライスする例。
```rust
let a = [1, 2, 3, 4, 5];

let slice = &a[1..3];
```

# 構造体
他プログラミング言語同様に構造体が扱える
```rust
struct User {
    username: String,
    email: String,
    sign_in_count: u64,
    active: bool
}
```

🚧: 可変の設定は、要素全体にしか適用できない制約がある

💡: 仮引数名と構造体のフィールド名が同じなら代入時にフィールド名を省略できる
```rust
fn build_user(email: String, username: String) -> User {
    User {
        email,
        username,
        active: true,
        sign_in_count: 1,
    }
}
```

構造体を試しに出力したい場合は、デバッグ用の表示設定とprintlnの出力を以下のように変えるとできる
```rust
#[derive(Debug)]
struct Rectangle {
    width: u32,
    height: u32
}

fn main() {
    let rect1 = Rectangle {width: 30, height: 50};

    println!("rect1 is {:?}", rect1);
    println!("rect1 is {:#?}", rect1); // 要素ごとに改行してくれる
}
```

```
> rect1 is {width: 30, height: 50}
```

と出力される

# メソッド記法
fnと同じ記法や戻り値を返しができる。

構造体をベースに関数を書く感じで構造体に紐づくように機能を拡張できる。`impl` で実装する。

```rust
struct Rectangle {
    width: u32,
    heigth: u32,
}

impl Rectangle {
    fn area(&self) -> u32 {
        self.width * self.heigth
    }
}
```
同一名の構造体をベースにすることをコンパイルが理解するため `impl` 以降は、関数 + `&self` シグネチャを呼び出すだけで良い。

引数の振る舞いは前述されている関数の引数と同じ振る舞いが取れるため、実装する機能に合わせて参照、借用を使い分けると良い。

Rustは、メソッド呼び出しで、**自動参照および参照外し**が行われるため、例えば以下コードは前者が所有権と自動参照を用いることで明瞭に書くことができる。
```rust
p1.distance(&p2);
(&p1).distance(&p2);
```

読み込み専用なら、メソッドに `&self` シグニチャを設定して

書き込みなら、`&mut self` シグニチャを設定する

よって、実際に所有権を使った実装は簡単にできる。

## 構造体を引数に取る

メソッドの引数に構造体を設定できるため、設定した構造体から任意の処理を実装できる。
```rust
impl Rectangle {
    fn can_hols(&self, other: &Rectangle) -> bool {
        self.width > other.width && self.heigth > other.heigth
    }
}
```

## 関連関数

`self`を持たない関数を実装することができる。これを `関連関数` という。

⚠️: 関連関数は、メソッドではないため呼び出し方には気をつける必要がある。

以前使った、 `String::from()` も関連関数

実装は、以下の通り
```rust
impl Rectangle {
    fn square(size: u32) -> Rectangle {
        Rectangle { width:size, heigth: size }
    }
}

fn main() {
    let sq = Rectangle::square(3);

    println!("Squre size: {:#?}", sq);
}
```

## implブロック
各構造体に、implブロックを定義できるが基本的には、まとめる。複数が有効になるパターンとして、ジェネリック型とトレイトがある

### `&self`を使った代入先による関数呼び出し
implブロック内の関数として `&self`を入力値として定義すると代入した変数からその関数を呼び出すことができる。

```rust
pub struct Expression {
	pub numbers: Vec<i32>,
	pub operators: Vec<Operator>,
}

impl Expression {
	fn new() {
		return None
	}
	
    fn evaluate(&self) -> Result<i32, CalcError> {
        let mut result = self.numbers[0];
        
        for (num, op) in self.numbers.iter().skip(1).zip(self.operators.iter()) {
            result= op.calculate(result, *num)?;
        }

        Ok(result)
    }
}

fn main() {
	let expr = Expression::new();
	// 代入された変数から関数を呼び出せる
	expr.evaluate();
}
```


### Selfを使って自身の構造体を返す
implブロックで作った関数の返り値として `Self` を使い自身の構造体を返すテクニックがある
```rust
struct Mystruct {
	value: i32
}

impl Mystruct {
	fn my_function(input: i32) -> Result<Self, Err> {
		let val = input;
		Ok(Self {
			value: val?
		})
	}
}
```

このように、Mystruct構造体自体を返り値にすることもできる。
ただし、`Ok` で定義した `Self`に構造体の中身を埋める必要がある。

# Enum
Rustのenumは、代数的データ型に酷似している

`impl` を使って構造体同様にメソッド等の実装ができる。

⚠️: null機能は、Rustには無い

nullの代わりに、enumを使って値の不在を表現する。

# matchによる制御フロー

matchを使うと入力された値を条件に応じて処理を実行することができる

```rust
let some_u8_value = Some(3u8);

match some_u8_value {
    Some(3) => println!("there"),
    _ => (),
}
```

`_` を条件に加えることでどれにもマッチしない場合の処理を追加でき包括性が高まる

# `if let` を使った制御フロー

matchよりも簡易的な制御フローを使いたい場合は、`if let` が用いられる

```rust
let some_u8_value = Some(3u8);

// 従来のmatchによる制御
match some_u8_value {
    Some(3) => println!("there"),
    _ => (),
}

// if letを使った制御フロー
if let Some(3) = some_u8_value {
    print!("three");
}
```

`Some(3)` かどうかの判定は `if let` のほうが簡易に書けるが `match` と比べて包括性が損なわれる。
どちらを採用するかは、簡易性が包括性よりも重視された場合は、 `if let` を採用という感じで考える。

また、 `if let` は一つのパターンマッチのみしか扱えない制約がある。

# モジュールシステム
パッケージ、ファイル、クレートなどの管理、公開をまとめて扱うシステムを **モジュールシステム** と呼ばれる。

モジュールシステムには、以下が含まれる
- パッケージ: クレートをビルド、テスト、共有することができるCargoの機能
- クレート: ライブラリか実行可能ファイル(バイナリ)を生成する木構造のモジュール郡
- モジュールと use: パスの構成、スコープ、公開するかを制御する
- パス: 要素(例えば、構造体、関数、モジュール)に名前を付ける方法

## パッケージとクレート
クレートは、バイナリかライブラリのどちらか。**クレートルート**によってRustライブラリの開始点となる、クレートのルートモジュールを作るソースファイルのこと。

パッケージは、ある機能郡を提供する一つ以上のクレート。パッケージは、**Cargo.toml**という、それらクレートをどうビルドするか説明するファイルを持つ。

パッケージ、クレートのルール
- パッケージ: 0 ~ 1個より多くライブラリクレートを持ってはいけない
- バイナリクレート: ライブラリクレートの数に制限は無いが、1つ以上のクレートが必要

```
cargo new my-project
```

と実行すると以下の **Cargo.toml** が作れる

```toml
[package]
name = "my-project"
version = "0.1.0"
edition = "2024"

[dependencies]
```

tomlファイル内で **src/main.rs** について言及が無いがこれは、Rustの慣習でパッケージと同じ名前を持つバイナリクレートがクレートルートであるため。

パッケージディレクトリに、 **src/lib.rs** が含まれていたらパッケージには、パッケージと同じ名前のライブラリクレートが含まれており、 **src/lib.rs**がそのクレートルートだと判定される。

Cargoは、クレートルートを `rustc` に渡し、ライブラリやバイナリをビルドします。

同一プロジェクトに **src/main.rs** と　**src/lib.rs**があれば２つのクレートは2つとなり、どちらもパッケージと同じ名前を持つライブラリクレートとバイナリクレートになる。

また、ファイルを **src/bin**ディレクトリ以下に置けば、パッケージは、複数のバイナリクレートを持つことになる

クレートを定義して他プロジェクトで使う、例えば、`rand` クレートを自プロジェクトに追加すると `rand`というクレートの名前でクレートにアクセスでき、その中にある `Rng` というトレイトが使える。

アクセス方法はこんな感じ
```rust
rand::Rng
```

このようにクレートに紐づくようにトレイトが定義されるため、同一名の **Rng** を実装しても名前衝突を防げる。

## モジュールを定義して、スコープとプライバシーを制御する
libモジュールを作るときは以下のようにnewコマンドを叩く
```
cargo new --lib <project>
```

モジュール例(レストランの接客の振る舞い)
```rust
mod front_of_house {
    mod hosting {
        fn add_to_waitlist() {}

        fn seat_at_table() {}
    }

    mod serving {
        fn take_order () {}

        fn serve_order() {}

        fn take_payment () {}
    }
}
```

モジュールと関数の親子関係は、以下ディレクトリに似た木構造でcreate以下に作られる

![alt text](image-1.png)

## モジュールツリーの要素を示すパス
関数呼び出しのパスは2種ある
- 絶対パス: クレートの名前か `create` という文字列を使うことで、クレートルートからスタートする
- 相対パス: `self`, `super` または今のモジュール内の識別子を使うことで、現在のモジュールからスタートする


## pathを `pub` キーワードで公開

`pub` を使うことでモジュール・関数を公開できる

## useキーワードについて

```rust
mod front_of_house {
    pub mod hosting {
        pub fn add_to_waitlist() {}
    }
}

// クレートから絶対パスで呼びし
use crate::front_of_house::hosting;

// 今のクレートの位置から相対パス
use self::front_of_house::hosting;

pub fn eat_at_restaurant() {
    hosting::add_to_waitlist();
    hosting::add_to_waitlist();
    hosting::add_to_waitlist();
}
```

`use` キーワードは上記のコードのようにフルパスの呼び出しからシンボリックリンクを貼るような形でコード省略を助けてくれる。

他に、パッケージ呼び出しも以下のように行える。
```rust
// 以下のように呼び出せる
use std::collections::HashMap;
use std::fmt;
use std::io;
use std::io::Result as IoResult; // 別名ができる！

pub fn eat_at_restaurant() {
    let mut map = HashMap::new();
    map.insert(1, 2);
}

// このように、fmt/ioでResult
fn function1() -> fmt::Result {}　// 出力の型定義もできちゃう
fn function() -> io::Result<()> {}
fn function3() -> IoResult<()> {}
```

`pub use` を使うことで同一プロジェクトの他のクレートから読み込むように自プロジェクトに再公開することができる。

## 外部ファイル呼び出し

front_of_house.rsとして以下を定義。
```rust
pub mod hosting {
    pub fn add_to_waitlist() {}

    fn seat_at_table() {}
}
```

lib.rsで呼び出しを以下のように行う。
```rust
mod front_of_house;
use crate::front_of_house::hosting;
```

## 同一プロジェクトでのモジュールの呼び出し
lib.rs以外は、main.rsでモジュールとして `mod`を使った呼び出しが必要である

src/main.rs
```rust
mod my_module;
```

この呼び出しをしたら、main.rsでも他ファイルでもクレートを呼びだせる

src/main.rs
```rust
mod my_module;
use my_module::My_function;
```

src/other_module.rs
```rust
use my_module::My_function;
```


# コレクション
複数の値を含むことができるデータ型でこれはヒープに確保される。

以下のデータ型が持たれる
- ベクタ型: 可変長の値を並べて保持できる
- 文字列: 文字のコレクション
- ハッシュマップ: 値を特定のキーと紐づけできるような、一般的なデータ構造のマップの実装である

## ベクタ型
単体のデータ構造で、複数の値を保持できるが同じ型しか保持できない。

変数定義して、挿入したい場合可変で定義すると良い。
```rust
let mut v = Vec::new();

v.push(5);
v.push(6);
v.push(7);
v.push(8);
```

vectorを `drop` すれば、内包する要素も全て解放される。

定義した以上の要素にアクセスするとパニックを起こして実行がクラッシュする。

以下のように要素を借用すると解放されたメモリに対して終端の値追加でエラーが発生する。
```rust
let mut v = vec![1, 2, 3, 4, 5];

let first = &v[0];

v.push(6);
```

別データ型をベクタ型に定義したくなったらenumを使えば良い
```rust
enum SpreadsheetCell {
    Int(i32),
    Float(f64),
    Text(String),
}

let row = vec![
    SpreadsheetCell::Int(3),
    SpreadsheetCell::Text(String::from("blue")),
    SpreadsheetCell::Float(10.12),
]
```

## 文字列
Rustの文字列は以下性質により複雑性を持つ
- ありうるエラーを晒す
- 複雑なデータ型
- UTF-8にエンコードされる

**文字列とは？**

言語の核としては、1種類しか文字列型しか存在しない。

その他にも、標準ライブラリとして、 `OSString`, `OSStr`, `CString`, `CStr` を持つ。また、ライブラリクレートにより、より選択肢が広がる。


文字列の追加
```rust
let mut s = String::from("lo");
s.push('l');
```

```
> lol
```

文字列の連結
```rust
let s1 = String::from("Hello, ");
let s2 = String::from("world!");

// +演算子で結合ができる
let s3 = s1 + &s2;
println!("{}", s3);
```

```
> Hello, world!
```

`+` 演算子は、 `add`メソッドを呼び出す。シグニチャは以下の通り。
```rust
fn add(self, s: &str) -> String {
```

このシグニチャは、最初の文字列引数に2番目の文字列引数の参照を渡す。シグニチャのselfには、 `&` が無いため `s1` は `add`の呼び出しによりムーブされることになる。

これで最初の文字列引数の所有権を移動することでコピーよりも効率よく文字列結合を行える。

所有権渡さずに連結してー！場合は、 `format!` マクロを使う
```rust
let s1 = String::from("tic");
let s2 = String::from("tac");
let s3 = String::from("toe");

let s =format!("{}-{}-{}", s1, s2, s3);
println!("{}", s);
```

文字列からインデックス使ったアクセス→サポートしてない
```rust
let s1 = String::from("hello!");
// エラーコード
let h = s1[0];
```
エラー原因は、Rustの文字列での文字列の持ち方を理解すると良い

アクセスする方法は、文字列スライスを活用すれば良い
```rust
let  hello = "Здравствуйте";
let s = &hello[0..4];
println!("{}", s);

> Зд

let s = &hello[0..1];

> アクセスできる文字列とバイト数が合っておらず実行パニック
```
扱う文字列の最小バイト数を把握しないと実行パニックを起こす。

スライス以外にも、 `chars()`, `bytes()` メソッドを使った文字列アクセスができる。
```rust
for c in "Здравствуйте".chars() {
    println!("{}", c);
}

for b in "Здравствуйте".bytes() {
    println!("{}", b);
}
```
charsメソッドは、直接charにアクセスし、bytesメソッドは、メモリ位置を返す。

### 文字列のparse
Stringのparseメソッドを活用すれば標準入力などされたString型をu32などに変換が可能。

#### Examples

Basic usage:

```rust
let four: u32 = "4".parse().unwrap();

assert_eq!(4, four);
```

Using the ![turbofish](#Turbofishを使った型指定) instead of annotating `four`:

```rust
let four = "4".parse::<u32>();

assert_eq!(Ok(4), four);
```
Ok関数を使う理由は、parse関数の出力がResult型のため。

Failing to parse:

```rust
let nope = "j".parse::<u32>();

assert!(nope.is_err());
```

## ハッシュマップ
キーバリューで値を持つデータ型。キーのデータ型は自由。ただし、キー、バリュー共に全て同一の型に合わせる必要がある。

呼び出し方は以下の通り。
```rust
let mut scores = HashMap::new();
scores.insert(String::from("Blue"), 10);
scores.insert(String::from("Yellow"), 50);
```

値の組み合わせを `iter` メソッドを使って以下の通り作ることができる。
```rust
let teams = vec![String::from("Blue"), String::from("Yellow")];
let initial_scores = vec![10, 50];

let scores: HashMap<_, _> = teams.iter().zip(initial_scores.iter()).collect();
```

`HashMap<_, _>` を型注釈の詳細を省ける。

所有権について。 `i32`のように `Copy`トレイトがある場合は、値のコピーがされ、 `String`は所有権のムーブがされる。

以下のようにHashmapへの代入を行うと元の変数は所有権を失う。
```rust
let field_name = String::from("Favorite color");
let field_value = String::from("Blue");

let mut map = HashMap::new();
map.insert(field_name, field_value);
```

Hashmap要素へのアクセス
```rust
let mut scores = HashMap::new();

scores.insert(String::from(("Blue")),10);
scores.insert(String::from("Yellow"), 50);

let team_name = String::from("Blue");
let score = scores.get(&team_name);
for (key, value) in &scores {
    println!("{}: {}", key, value);
}
```

```
>
Blue: 10
Yellow: 50
```

要素の上書き
```rust
let mut scores = HashMap::new();

scores.insert(String::from("Blue"), 10);
scores.insert(String::from("Blue"), 25);

scores.entry(String::from("Yellow")).or_insert(50);
// キーが既出のため上書きされない
scores.entry(String::from("Blue")).or_insert(50);

println!("{:#?}", scores);
```

`insert`メソッドを使って同一キーに重ねて実行すると上書きがされ、`or_insert`メソッドは既出キーへの挿入を見送る処理が書ける。


古い値を活用する場面
```rust
let text = "hello world wonderful world";

let mut map = HashMap::new();

for word in text.split_whitespace() {
    let count = map.entry(word).or_insert(0);
    *count += 1;
}

println!("{:?}", map);
```
`count` は、代入後に参照外しを `*` を使って行うことで、古い値に基づいた計算を実現する。
また、 forループの終端でスコープを抜けるため、これらの変更は全て安全に行われる。

# エラー処理
Rustのエラーには、2種ある。
- 回復不能なエラー : 境界値を超えたなどバグ的挙動を指す。`panic!`マクロを呼びだす。
- 回復可能なエラー : パッケージ、ファイル読み込みなど再実行による修正されるものを指す。 `Result<T, _>` が出力される。


## `panic!`
基本的には、スタックを巻き戻す。しかし、巻き戻し対象が多いと実行可能ファイルでスタック巻き戻しを含めた処理をビルドする必要があり実行可能ファイルが膨らむ、その実行可能ファイルを極力小さくしたい場合は、異常終了を設定できる。

異常終了は、 `Cargo.toml`で以下のように設定できる。
```toml
[profile.release]
panic = 'abort'
```

使い所は、サーバーで継続的に実行させるリリースモードなどになる。

以下、環境変数を設定するとバックトレースを表示する
```
RUST_BACKTRACE=1
```

## Result型を使ったエラー処理の制御
Result型が返される。成功した場合は、ジェネリック型を返し、失敗するとErrを返す。

matchを使うとResultの `Ok`と `Err` の返り値に応じた処理ができる。
```rust
let f = File::open("hello1.txt");

let f = match f {
    Ok(file) => file,
    Err(ref error) if error.kind() == ErrorKind::NotFound => {
        match File::create("hello1.txt") {
            Ok(fc) => fc,
            Err(e) => {
                panic!(
                    "Tried to create file but there was a problem: {:?}",
                    e
                )
            },
        }
    },
    Err(error) => {
        panic!(
            "There was a problem opening the file: {:?}",
            error
        )
    },
};
```

`Err` を返すときの処理を変更できる。
```rust
let f = File::open("hello2.txt").unwrap();
let f = File::open("hello2.txt").expect("Failed to open hello2.txt");
```

関数などの実行のエラー結果を呼び出し元に委譲するエラー委譲が作れる。
```rust
fn read_username_from_file() -> Result<String, io::Error> {
    let f = File::open("hello1.txt");
    let mut f = match f {
        Ok(file) => file,
        Err(e) => return Err(e),
    };
    let mut s = String::new();
    match f.read_to_string(&mut s) {
        Ok(_) => Ok(s),
        Err(e) => Err(e),
    }
}
```
上記、関数は、実行結果をResult型かつタブルの中身を成功時に文字列、エラー時に `std::io::Error` を返すように構築できる。
こうすることで、エラー発生を関数でキャッチし、その結果を呼び出し元で好きに処理できるように　**エラー委譲**　ができる。

```rust
fn main() {
    // 呼び出してResult型の返り値に合わせて呼び出し元で実行結果を制御できる
    let f = read_username_from_file();
    let f = match f {
        Ok(file) => file,
        Err(error) => {
            panic!(
                "There was a problem opening the file: {:?}",
                error
            )
        },   
    };

    // このように呼び出すだけならエラーになっても呼び出し元で何も処理がされないため、そのまま処理が続行される
    let f = read_username_from_file();
}
```

エラー委譲の書き方は、 `?` を使うと簡略化できる。
```rust
fn read_username_from_file_p2() -> Result<String, io::Error> {
    let mut f = File::open("hello.txt")?;
    let mut s = String::new();
    f.read_to_string(&mut s)?;
    Ok(s)
}
```

`?` 演算子は結合でき以下のように更に簡略化できる。
```rust
fn read_username_from_file_p3() -> Result<String, io::Error> {
    let mut s = String::new();
    
    File::open("hello.txt")?.read_to_string(&mut s)?;
    
    Ok(s)
}
```

`?` 演算子はreturnされる型との互換性を保つために、 `Result`を返す関数での利用に制限される。

## return 1による異常終了を返す
panicマクロ以外にも `std::process::exit(1)`という関数でプロセスの異常終了を実行することができる。

## `eprintln!`マクロを使ったエラーの標準出力
`eprintln!`マクロを使うとエラーの標準出力ができる。
上述している `exit(1)`の前に実行してエラー表示をしつつ異常終了させる方法も取れる。
ここまで組み合わせたら `panic!`マクロのほうがスマートに書けそうなきがしてきた。

## Result型 or panic!か
Rustyな書き方を目指す場合はなるべくResult型を使ったエラー処理にする。
ただし、場合に合わせて、エラーの返し方が回復不能であることを明示する場合は、 `panic!`、エラー委譲したい場合は、 `Result`の判断基準とする。

コード別での使い所

| コードタイプ | 説明 |
| --- | --- |
| プロトタイプ・テストコード | unwrap, exceptを使って検証で落ちるべき箇所を表明する。そのため、Result型・panic!よりも簡易に使え検証に向いている
| Okが返されて追加で何か処理を行うとき | Result型を返す関数を使って返り値から呼び出し元で適宜処理をする
| panic!が有効な箇所 | 無効な値、矛盾する値、行方不明な値が入力されたときに異常終了をさせることで関数、ライブラリ利用者に早期にバグを知らせることができる。(例として、配列で境界値外の値にアクセスするとデフォルトでpanic!を返す)

## 検証に向けた独自の型作成
独自の型を定義することで値検証を集約して処理パフォーマンスを上げることに寄与できる。
```rust
pub struct Guess {
    value: u32,
}

impl Guess {
    pub fn new(value: u32) -> Guess {
        if value < 1 || value > 100 {
            panic!("Guess value must be between 1 and 100, got {}.", value);
        }

        Guess { value }
    }

    pub fn value(&self) -> u32 {
        self.value
    }
}
```
# ジェネリック型、トレイト、ライフタイム
ジェネリックは、概念の重複を取り扱うための機能で、具体型や他のプロパティの抽象的な代役になる。

具体は、 `Option<T>`, `Vec<T>`, `HashMap<K, V>`, `Result<T, E>`が挙げられる。

トレイトを使うことで、ジェネリックな方法で振る舞いを定義でき、ジェネリック型にトレイトを組み合わせて特定の振る舞いをさせることができる。

ライフタイムとは、コンパイラに参照がお互いにどう関係しているのか情報を与える一種のジェネリック型である。ライフタイムによって、コンパイラに参照が有効であることを示し、信頼性高い値のやり取りを可能にする。

## ジェネリック型の定義
再利用可能な関数を作ると特定の型に合わせた引数による拘束がある。ここにジェネリック型を定義することによって型による拘束を無くした関数の引数を定義できる。

ざっくり以下のように書ける。
```rust
fn largest<T: std::cmp::PartialOrd>(list: &[T]) -> T {
    let mut largest = &list[0];

    for &item in list.iter() {
        if item > *largest {
            largest = &item;
        }
    }

    largest
}
```

構造体でもジェネリック型を設定できるため、構造体のデータ型定義の拘束を無くせる。
```rust
struct Point<T> {
    x: T,
    y: T,
}

fn main() {
    let integer = Point { x: 5, y: 10 };
    let float = Point { x: 1.0, y: 4.0 };
}
```

ジェネリック型のデータ型の定義の数(TとかUとかに合わせて)を構造体で同じデータ型に揃える必要あり。
```rust
// エラーコード
let wont_work = Point { x: 5, y: 4.0 };
```
ジェネリック型の種類が増えるほど管理がしづらい状況になる。

enum定義も同様に使える。以下のように書く。
```rust
enum Option<T> {
    Some(T),
    None,
}
```

メソッド定義で以下のように実装できる。
```rust
struct Point<T> {
    x: T,
    y: T,
}

impl<T> Point<T>  {
    fn x(&self) -> &T {
        &self.x
    }
}

fn main() {
    let p = Point { x: 5, y: 10 };
    println!("p.x = {}", p.x());
}
```

メソッド定義は以下のようにジェネリック型が使える。
```rust
struct PointP2<T, U> {
    x: T,
    y: U,
}

impl<T, U> PointP2<T, U>  {
    fn mixup<V, W>(self, other: PointP2<V, W>) -> PointP2<T, W> {
        PointP2 {
            x: self.x,
            y: other.y,
        }
    }
}

fn main() {
    let p1 = PointP2 { x: 5, y: 10.4};
    let p2 = PointP2 { x: "Hello", y: 'c'};

    let p3 = p1.mixup(p2);

    println!("p3.x = {}, p3.y = {}", p3.x, p3.y);
}
```

Rustは、コンパイルの時点でジェネリック型に入る値は代入値から確定させてコンパイルするため、ジェネリック型を利用してもパフォーマンスに影響無しにできる。
よって、コードの記述も簡略化できつつパフォーマンスそのままの結果を得られる。

## トレイト
トレイトを使うと、共通の振る舞いを抽象して機能を共有することができる。他の言語でいう所謂、インターフェース的振る舞いをする。


トレイトの実装は、こうするのじゃ。
```rust
pub struct NewsArticle {
    pub headline: String,
    pub location: String,
    pub author: String,
    pub content: String,
}

pub trait Summary {
    fn summarize(&self) -> String;
}

impl Summary for NewsArticle {
    fn summarize(&self) -> String {
        format!("{}, by {} ({})", self.headline, self.author, self.location)
    }
}

pub struct Tweet {
    pub username: String,
    pub content: String,
    pub reply: bool,
    pub retweet: bool,
}

impl Summary for Tweet {
    fn summarize(&self) -> String {
        format!("{}: {}", self.username, self.content)
    }
}

fn main() {
    let tweet = Tweet {
        username: String::from("horse_ebooks"),
        content: String::from(
            "of course, as you probably already know, people",
        ),
        reply: false,
        retweet: false
    };

    println!("1 new tweet: {}", tweet.summarize());
}
```

トレイトの実装は、関数に似ており、型に `impl`を使ってメソッドを追加することで実装ができる。

実装の制約として、ローカルの実装のみスコープとする。この制約により、ライブラリやその他外部クレートとの衝突を防げる。

デフォルト実装もでき以下のように書ける。

```rust
pub trait Summary {
    fn summarize_author(&self) -> String;

    fn summarize(&self) -> String {
        format!("(Read more from {}...)", self.summarize_author())
    }
}

impl Summary for NewsArticle {
    fn summarize_author(&self) -> String {
        format!("@{}", self.author)
    }
}
```
これでsummarizeを実装せずに置くと `Summary` traitで実装した処理が実行される。

トレイトを引数として渡すことができる。
```rust
pub fn notify(item: &impl Summary) {
    println!("Breaking news: {}", item.summarize());
}
```

トレイト境界というsyntax sugarがあり引数が増えた場合により簡易にトレイトを引数にできる。
```rust
pub fn notify<T: Summary>(item: &T) {
    println!("Breaking news: {}", item.summarize());
}

// 以下のようにまとまる
pub fn notify<T: Summary>(item: &T, item2: &T) {
    println!("Breaking news: {}", item.summarize());
}
```
上記の書き方だと、引数全て型を統一する必要がある。


`Summary` トレイトを返すことができる関数も作れる。
```rust
fn returns_summarizable() -> impl Summary {
    Tweet {
        username: String::from("horse_ebooks"),
        content: String::from(
            "of course, as you probably already know, people",
        ),
        reply: false,
        retweet: false,
    }
}
```

関数をジェネリック型にして好きなデータ型を導入したい場合は、syntax sugarを活用して以下のように書くと良い。
```rust
fn largest<T: PartialOrd + Copy>(list: &[T]) -> T {
    let mut largest = list[0];

    for &item in list.iter() {
        if item > largest {
            largest = item;
        }
    }

    largest
}
```

Copyによって引数でCopy機能を有効化できる。

## ライフタイムについて
ライフタイムとは、参照が有効になるスコープのこと。Rustでは、参照に全てライフタイムを持つ。
また、暗黙的に型と同様に推論される。


主な、役割は、ダングリング参照を回避するため。

ライフタイムが切れる例
```rust
let r;

{
    let x = 5;
    r = &x;
}

println!("r : {}", r);
```
x変数がr変数よりもスコープが短く参照切れが起こる。

ライフタイム注釈記法を使うことで以下のようにスコープがどこに位置するかコンパイラが困る(人も判断付きづらい)場合にライフタイムを明示することができます。
```rust
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() {
        x
    } else {
        y
    }
}
```

ifスコープでxなのかyが有効なのかが実行まで不明になる。これを `'a` というライフタイム注釈を追加することで `'a`　と同じライフタイムに統一できてコンパイルできるようになる。

# Test
関数に `#[test]` 注釈を付けることでテストコードとして機能させられる。

以下のようにテストコードが書ける。
```rust
#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
        assert_eq!(2 + 2, 4)
    }
}
```

debugトレイトを構造体、enumに定義するとテストエラー時に結果を出力できる。
```rust
#[derive(Debug)]
struct Rectangle {
    width: u32,
    height: u32,
}

impl Rectangle {
    fn can_hold(&self, other: &Rectangle) -> bool {
        self.width > other.width && self.height > other.height
    }
}
```

`#[derive(PartialEq, Debug)]` を追加すると以下のように出力される。
```
---- tests::it_adds_two stdout ----

thread 'tests::it_adds_two' panicked at src/lib.rs:62:9:
assertion `left == right` failed
  left: 4
 right: 5


failures:
    tests::another
    tests::it_adds_two

test result: FAILED. 3 passed; 2 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
```

テスト結果はformatマクロで標準出力される。 例えば、 `assert!`で第2引数、第3引数を指定することで出力結果を変更できる。
```rust
#[test]
fn greeting_contains_name() {
    let result = greeting("Carol");
    assert!(
        result.contains("Carol"),
        "Greeting did not contain name, value was `{}`",
        result
    );
}
```

標準出力結果
```
---- tests::greeting_contains_name stdout ----

thread 'tests::greeting_contains_name' panicked at src/lib.rs:73:9:
Greeting did not contain name, value was `Hello!`
```

`#[should_panic(expected = "Guess value must be less than or equal to 100")]` とトレイト追加するとこのメッセージ以外はテストエラーが出るようになる。


Result型を使った出力をテストすることもできる。
```rust
#[test]
fn it_works() -> Result<(), String> {
    if 2 + 2 == 4 {
        Ok(())
    } else {
        Err(String::from("two plus two does not equal four"))
    }
}
```
成功すると `Ok`が返り、失敗すると `Err` が返る。

testを選択して実行できる。
```
cargo test <test name>
```

正規表現的に実行できる。前置で実行可能である。
```
cargo test <test name *>
```

`#[ignore]` を使うことでテスト実行を無視できる。
```rust
#[test]
#[ignore]
fn expensive_test() {
    // 
}
```

ignoreのみ実行したい場合は以下実行する。
```
cargo test -- --ignored
```

## Result型のテスト
Result型を返す関数のテストは比較する値を `Ok`で囲むことで `.unwrap()`を使わずに比較ができる
```rust
assert_eq!(Ok(const_value), return_result.function());
```

## `#[cfg(test)]` 意味
`#[cfg(test)]` を使うことで、このモジュールを含むテストはビルド時にスキップするように指示できる。
これは、単体テストで使うのに適しておりビルド時に結合ができるかの確認をする結合テストでは、このモジュールは使わない。

## 非公開関数のテスト
Rustでは、非公開関数のテストが容易にできる。

```rust
fn internal_adder(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn internal() {
        assert_eq!(4, internal_adder(2,2));
    }
}
```

## 結合テスト
`./tests`ディレクトリを作ることでCargoが結合テストコード用のディレクトリだと認識でテストコードの実行をしてくれる。

```
cargo test
```
で全てのテストコードを実行できるが、単体テストでエラーがある場合は、統合テストはスキップされる。

## 統合テストでのサブモジュール
testsディレクトリ以下に、 `common.rs`を作ることで統合テストコード用のヘルパー関数などをまとめることができる。

ただし、このコードファイルが有ると毎度標準出力されるため、`tests/common/mod.rs`とサブモジュールファイルを作ると標準出力を減らせる。

## バイナリクレート用の結合テスト
`src/lib.rs`が無く `src/main.rs`のみの場合は、 `extern crate`のように呼び出して結合テストを実行することができない。

# イテレータ・クロージャ
Rustには、イテレータとクロージャ機能を持つ。
- クロージャ: 変数に保存できる関数に似た文法要素
- イテレータ: 一連の要素を処理する要素

## クロージャ
所謂、匿名関数で、有る場所でクロージャを生成して別の場所で評価できる。

クロージャの書き方。
```rust
let expensive_result = |num| {
    println!("calculating slowly...");
    tread::sleep(Duration::from_secs(2));
    num
};
```

クロージャの様々な定義方法。
```rust
let add_one_v2 = |x: u32| -> u32 { x + 1 };
let add_one_v3 = |x| { x + 1 };
let add_one_v4 = |x| x + 1 ;
```
1行目は、型注釈を加えて引数、返り値の型を明示している。2行目は、型注釈無し。3行目

`|num|` が引数になる。複数の引数がある場合は、 `|param1, param2|` と定義すればよい。

呼び出し方。
```rust
expensive_result(intensity)
```

これでも、同一の匿名関数が複数回実行されることになる。これを一度だけ実行して以降は、評価結果を返すようにしたい。

クロージャは複数呼び出しで別の型を入力すると型エラーになる。
```rust
let example_clousure = |x| x;
let s = example_clousure(String::from("hello"));
let n = example_clousure(5);
```

3つの方法で環境から値をキャプチャできる。方法は3つある。
- `FnOnce` : クロージャの環境として知られている内包されたスコープからキャプチャした変数を消費する。キャプチャした変数を消費するため、クロージャはこの変数から所有権を剥奪するためこのクロージャは2回以上所有権を利用できない。
- `FnMut` : 可変で値を借用するため、環境を変更することができる。
- `Fn` : 環境から値を不偏で借用できる。

## イテレータ

イテレータは以下の振る舞いで次の要素を返す。
```rust
fn iterator_demonstration() {
    let v1 = vec![1, 2, 3];

    let mut v1_iter = v1.iter();

    assert_eq!(v1_iter.next(), Some(&1));
    assert_eq!(v1_iter.next(), Some(&2));
    assert_eq!(v1_iter.next(), Some(&3));
    assert_eq!(v1_iter.next(), None);
}
```
iteratorメソッドを変数に入れる場合、 `next()`メソッドを使うと値が変わるため `mut`による可変での定義が必要となる。

`Iterator`トレイトを実装するときは、 `Item`型の定義も必須。
```rust
pub trait Iterator {
    type Item;

    fn next(&mut self) -> Option<Self::Item>;
}
```


次にように`sum`メソッドを実行すると所有権が変数に移る。
```rust
#[test]
fn iterator_sum() {
    let v1 = vec![1, 2, 3];

    let v1_iter = v1.iter();

    let total: i32 = v1_iter.sum();

    assert_eq!(total, 6);
}
```
`sum`メソッド呼び出し後に再度、`v1_iter`を呼び出すとエラーが返される。

Rustのイテレータは怠惰で消費する必要が有る。
```rust
let v1: Vec<i32> = vec![1, 2, 3];
let v2:Vec<_> = v1.iter().map(|x| x + 1);
let v2:Vec<_> = v1.iter().map(|x| x + 1).collect();
```
2行目だと、所有権が消費されずメモリに残り続けるため実行時に警告が表示される。3行目で `collect()`メソッドを使うことで所有権を消費できる。
ついでにここで `map`を使うことで要素の一括処理を実現していることが分かる。

## 独自イテレータを作る
`Iterator`トレイトを使うことで独自のイテレータを実装できる。

以下の様に実装ができる。
```rust
struct Counter {
    count: u32,
}

impl Counter {
    fn new() -> Counter {
        Counter { count: 0 }
    }
}

impl Iterator for Counter {
    type Item = u32;

    fn next(&mut self) -> Option<Self::Item> {
        self.count += 1;

        if self.count < 6 {
            Some(self.count)
        } else {
            None
        }
    }
}
```

呼び出しは、以下のようにできる。
```rust
#[test]
fn calling_next_directly() {
    let mut counter = Counter::new();

    assert_eq!(counter.next(), Some(1));
    assert_eq!(counter.next(), Some(2));
    assert_eq!(counter.next(), Some(3));
    assert_eq!(counter.next(), Some(4));
    assert_eq!(counter.next(), Some(5));
    assert_eq!(counter.next(), None);
}
```

## iter応用
### step_by
要素を提供するときに区切りを設定し区切りの間をスキップした要素を渡す。
```rust
let a = [0, 1, 2, 3, 4, 5];
let mut iter = a.into_iter().step_by(2);

assert_eq!(iter.next(), Some(0));
assert_eq!(iter.next(), Some(2));
assert_eq!(iter.next(), Some(4));
assert_eq!(iter.next(), None);
```
このようなに `step_by(2)`の場合は、2区切りごとに要素を渡す。
この場合は、 `[0, 2, 4]`の配列が渡される。

### map()を使った要素別の内部処理
 イテレーターの中でクロージャーを呼び出し処理を実行する。
 例えば、以下のようなコードでは、各要素へ `*2`処理を実行する。
 ```rust
 #![allow(unused)]
fn main() {
    let a = [0, 2, 3];
    
    let mut iter = a.iter().map(|x| 2 * x);
    
    assert_eq!(iter.next(), Some(0));
    assert_eq!(iter.next(), Some(4));
    assert_eq!(iter.next(), Some(6));
    assert_eq!(iter.next(), None);
}
 ```

ただし、内部で `println!`のようなマクロが実行されると遅延実行が発生してRust上で実行すらされない状況になる。
```rust
#![allow(unused)]
#![allow(unused_must_use)]

// don't do this:
fn main() {
    (0..5).map(|x| println!("{x}")); // これ遅延実行
    
    // it won't even execute, as it is lazy. Rust will warn you about this.
    
    // Instead, use a for-loop:
    for x in 0..5 {
        println!("{x}");
    }
}
```

### Combinators: and_then
map()に `and_then`を追加することで処理の成功時その値の評価を更に追加することができる。
参考: https://doc.rust-lang.org/rust-by-example/error/option_unwrap/and_then.html

```rust
#![allow(dead_code)]

#[derive(Debug)] enum Food { CordonBleu, Steak, Sushi, Salada }
#[derive(Debug)] enum Day { Monday, Tuesday, Wednesday }

// We don't have the ingredients to make Sushi.
fn have_ingredients(food: Food) -> Option<Food> {
    match food {
        Food::Sushi => None,
        _           => Some(food),
    }
}

// We have the recipe for everything except Cordon Bleu.
fn have_recipe(food: Food) -> Option<Food> {
    match food {
        Food::CordonBleu => None,
        _                => Some(food),
    }
}

// To make a dish, we need both the recipe and the ingredients.
// We can represent the logic with a chain of `match`es:
fn cookable_v1(food: Food) -> Option<Food> {
    match have_recipe(food) {
        None       => None,
        Some(food) => have_ingredients(food),
    }
}

// This can conveniently be rewritten more compactly with `and_then()`:
fn cookable_v3(food: Food) -> Option<Food> {
    have_recipe(food).and_then(have_ingredients)
}
```
cookable_v3関数の場合は、have_recipeで `Food::CordonBleu`の場合はNoneを返すそこに、`and_then`を追加することでhave_ingredientsの処理を追加し `Food::Sushi`の場合もNoneを返す評価の追加をしている。

### zip()
iterメソッドのメソッドチェーンで`zip()`を使うと同じ要素数を持つiterを結合させることができます。

コード例
```rust
#![allow(unused)]
fn main() {
    let nums = vec![1,2,3];
    let operators = vec!["a", "b"];
    let mut result = nums[0];
    
    for (num, op) in nums.iter().skip(1).zip(operators.iter()) {
        println!("{:?}, {:?}", num, op)
    }
}
```
出力結果
```
2, "a"
3, "b"
```


# CargoとCrates.io詳細

## cargo build
cargoには、プロファイルごとにビルド結果が異なる
```
cargo build
```
は、デフォルトでdevプロファイルをビルドし
```
cargo build --release
```
で、releaseプロファイルをビルドする。

profileごとに振る舞いを変えたい場合は以下のように書く。
```toml
[profile.dev]
opt-level = 0

[profile.release]
opt-level = 3
```

`profile.`以下でプロファイルを切る。ちなみに、`opt-level`はコンパイル時のコード最適化度合いで値が大きいほどコンパイルに時間を使うため、開発プロファイルは、`0`にするのが良い。


`///` を使うことでmarkdown形式のドキュメントを記述できる。その記述結果を`cargo doc` で出力できる。

書き方はこう。
```rust
/// Adds one to the number given.
/// 与えられた数値に１を足す。
/// 
/// # Ecample
/// ```
/// let five = 5;
/// 
/// assert_eq!(6, my_crate::add_one(5));
/// ```

pub fn add_one(x: i32) -> i32 {
    x + 1
}
```

以下の様な出力結果になる。
![alt text](image-2.png)

以下のようにセクションを記述をして関数、クレートの使い方を簡単に示せる。
- `Panics` : 関数が`panic!`が実行するケースを記述する。
- `Errors` : `Result`を返す場合に、エラーの種類の条件と種類を説明する。
- `Safety` : 関数を呼び出すときに `unsafe`な状態を説明する。

クレートについて説明をする場合は、 `//!`と記述してから説明文を書く。

```rust
//! # My Crate
//!
//! `my_crate` is a collection of utilities to make performing certain
//! calculations more convenient.  
```

以下出力結果。

パッケージ公開したいときは、[crates.io](https://crates.io/)を使う。ただし、公開は永久に残るため気をつけてオペレーションを行う。

バージョニングの取り下げ(yank)を以下コマンドでできる。
```
cargo yank --vers 0.0.1
```

cargo installを使うことでツールのインストールができる。
```
cargo install ripgrep
```
例えば、これで `rg`コマンドをインストールできる。

# スマートポインタ
ポインタは、メモリのアドレスを含む変数の一般的な概念。ポインタの利用は、`&`が一般的で参照権限を借用する。

スマートポインタは、ポインタの振る舞いに加えて、メタデータを追加する機能が有る。C++に端を発した概念で他の言語にもある。

以前の利用で以下のスマートポインタが有った。
- String
- `Vec<T>`
スマートポインタは、構造体を使い実装している。構造体と区別する特徴として、`Deref`、`Drop` トレイトを実装している。

## `Box<T>`
データをヒープに格納する。スタックに残るのは、ヒープデータへのポインタのみ。

`Box<T>`を活用することで、再帰的なデータ型を実現できる。

以下の様に再帰的なデータ構造を作るとする。
```rust
enum List {
    Cons(i32, List),
    Nil,
}

use List::{Cons, Nil};

fn main() {
    let list = Cons(1,
        Cons(2,
            Cons(3,
                Nil)));
}
```
これだと、コンパイラがスタックにどれだけデータが格納されるか実行されるまで不明な状態になりエラーとなる。

そのため、間接参照とヒープメモリ確保だけできるように変更をする。そこで `Box<T>`が使える。
```rust
enum List {
    Cons(i32, Box<List>),
    Nil,
}

use List::{Cons, Nil};

fn main() {
    let list = Cons(1,
        Box::new(Cons(2,
            Box::new(Cons(3,
                Box::new(Nil))))));
}
```

再帰的な定義の箇所をBoxに置き換えることで実現できる。

## `Deref`トレイトを使ってスマートポインタを通常の参照と同じように扱う
スマートポインタでも、通常のポインタ同様にポインタの変数代入後の変数の参照は、参照外しが必要。
```rust
let x = 5;
let y = Box::new(x);

assert_eq!(5, x);
assert_eq!(5, *y);
```

スマートポインタで行われる参照外しは、`Deref`トレイトを利用することで実現している。

自前で擬似的なBoxを実装すると以下のようになる。
```rust
struct MyBox<T>(T);

impl<T> MyBox<T> {
    fn new(x: T) -> MyBox<T> {
        MyBox(x) 
    }
}

use std::{self, ops::Deref};
impl<T> Deref for MyBox<T> {
    type Target = T;

    fn deref(&self) -> &T {
        &self.0
    }
}

fn main() {
    
    let x = 5;
    let y = MyBox::new(x);

    assert_eq!(5, x);
    assert_eq!(5, *y);
}
```

標準クレートに含まれる`Deref`を活用することで参照外しの実装が可能となる。`*y`は、実際には、以下の様にRustでコンパイルされる。
```rust
*(y.deref())
```

## `Drop`トレイト
値がスコープを抜けたときに走らせるコードを選択できるのが `Drop`トレイトの役割。これで値のメモリ解放をスコープ抜けた時点で自動で行いメモリリークによるエラーを防ぐ。

Dropによるコードは実装は以下の通りになる。
```rust
struct CustomSmartPointer {
    data: String,
}

impl Drop for CustomSmartPointer {
    fn drop(&mut self) {
        println!("Dropping CustomSmartPointer with data `{}`!", self.data);
    }
}

fn main() {

    let c = CustomSmartPointer { data: String::from("my stuff") };
    let d = CustomSmartPointer { data: String::from("other stuff") };

    println!("CustomSmartPointers created.");
}
```

これでスマートポインタが作られて値がスコープを抜けたときに以下のように出力されることが確認できる。
```
CustomSmartPointers created.
Dropping CustomSmartPointer with data `other stuff`!
Dropping CustomSmartPointer with data `my stuff`!
```
ここにあらゆるロジックを仕込むことでスコープ抜けたときに任意の処理を行わせる。

早期にスマートポインタを解放したい場合は、drop関数を活用する。

## `Rc<T>`
以下の様なデータ構造を実現したいとする。
![alt text](image-3.png)

`Rc<T>`を活用することで実現できる。
```rust
use std::rc::Rc;

enum List {
    Cons(i32, Rc<List>),
    Nil,
}

fn main() {
    let a = Rc::new(Cons(5, Rc::new(Cons(10, Rc::new(Nil)))));
    let b = Cons(3, Rc::clone(&a));
    let c = Cons(4, Rc::clone(&a));
}
```
`Rc::clone`を使うことでデータのディープコピーを避けられる。

`Rc::clone()`によって参照カウントを増やせる。この参照カウントが0にならない限り元の`Rc<T>`はメモリから返却されない。

このデータ型は、シングルスレッドでの利用を想定しているためマルチスレッドだとエラーになる。

## `RefCell<T>`
ReCell型は、保持するデータに対して単独の所有権を持つ。

Rustの借用規則
- いかなる時も、１つの可変参照か不偏参照のどちらかが可能となる
- 参照は常に有効でなければならない

ReCellは実行時に不変条件を強制する。

このデータ型は、シングルスレッドでの利用を想定しているためマルチスレッドだとエラーになる。

## スマートポインタのデータ型の選択について
- `Rc<T>`: 同じデータに複数の所有者を持たせることができる
- `Box<T>`: 不変借用、可変借用もコンパイル時に精査できる。
- `ReCell<T>`: 実行時に精査される可変借用を許可する。RefCellが不変でも値は可変化できる。

# 並行性
並列実行は、以下のように記述できる。
```rust
use std::thread;
use std::time::Duration;

fn main() {
    thread::spawn(|| {
        for i in 1..10 {
            println!("hi number {} from the spawned thread!", i);
            thread::sleep(Duration::from_millis(1));
        }
    });

    for i in 1..5 {
        println!("hi number {} from the main thread!", i);
        thread::sleep(Duration::from_millis(1));
    }
}
```

立ち上げスレッドの実行の保証に、`JoinHandle`を使うと良い。
```rust
use std::thread;
use std::time::Duration;

fn main() {
    let handle = thread::spawn(|| {
        for i in 1..10 {
            println!("hi number {} from the spawned thread!", i);
            thread::sleep(Duration::from_millis(1));
        }
    });

    for i in 1..5 {
        println!("hi number {} from the main thread!", i);
        thread::sleep(Duration::from_millis(1));
    }

    handle.join().unwrap();
}
```

`move`クロージャを使うことでスレッド間で所有権を移動できるが、強制的な所有権の借用はコンパイルエラーが返される。

## mpsc
Rustの並列処理の考え方として、メッセージでのやり取りによる値の共有を行うことでメモリ区切りでの並列実行で発生する値のデッドロックを防げる。

Go言語でも
> メモリを共有することでやり取りするな。代わりにやり取りすることでメモリを共有しろ。

という考え方に近いところがある。

Rustには、標準ライブラリとして `mpsc` (Multi producer, single consumer)という複数送信と単一受信を行えるようにするライブラリが実装されている。

以下の様にメッセージの送信と受信をする。
```rust
use std::sync::mpsc;
use std::thread;

fn main() {
    let (tx, rx) = mpsc::channel();

    thread::spawn(move || {
        let val = String::from("hi");
        tx.send(val).unwrap();
    });

    let received = rx.recv().unwrap();

    println!("Got: {}", received);

}
```

`recv()`というメソッドは、チャンネルの送信側が閉じるまで待つ。つまり、送信完了するまで待ってから受信後の処理を実行することができる。

Rustの所有権により、並列プログラミングで発生する並列間の値の不正な利用を防ぐ。例えば上記のコードで `val`は送信済み以降で値の再利用を試みるとコンパイルエラーになる。

送信器を複製して別のメッセージを送ることもできる。
```rust
let (tx, rx) = mpsc::channel();
let tx1 = mpsc::Sender::clone(&tx);
```

`tx1`という送信機を `tx`の複製として作られる。

## ミューテックス
ミューテックスとは、いかなる時も一つのスレッドにしかなんらかのデータのアクセスを許可しない、`mutual exclusion`(相互排他)を示す。

ミューテックスは、以下２つの規則を遵守する。
- データを使用する前にロックを試みる
- ミューテックスをロックしているデータの使用が完了したら、他のスレッドがデータの所有権を獲得できるようにアンロックが必須

Rustの型システムによってこれを安心して実装できる。

ミューテックスはロック機構により値の変更の衝突を防ぐが以下の様に複数のロックを繰り返し実行すると所有権を複数のスレッドに移そうとしてエラーがでる。しかもそのエラーは繰り返し文の中に紛れ込みコンパイラーが正しいエラー箇所を指し示せない。
```rust
use std::sync::Mutex;
use std::thread;
fn main() {
    let counter = Mutex::new(0);
    let mut handles = vec![];
    for _ in 0..10 {
        let handle = thread::spawn(move || {
            let mut num = counter.lock().unwrap();
            *num += 1;
    });
        handles.push(handle);
    }
    for handle in handles {
        handle.join().unwrap();
    }
    println!("Result: {}", *counter.lock().unwrap());
}
```

このように所有権を複数スレッドで共有したい場合は、`Arc<T>`型(アトミック型)を使うと安全に活用できる。

上述したエラーが発生するコードを下記のように変更するとコンパイルが成功する。
```rust
use std::sync::{Mutex, Arc};
use std::thread;
fn main() {
    let counter = Arc::new(Mutex::new(0));
    let mut handles = vec![];
    for _ in 0..10 {
        let counter = Arc::clone(&counter);
        let handle = thread::spawn(move || {
            let mut num = counter.lock().unwrap();
            *num += 1;
        });
        handles.push(handle);
    }
    for handle in handles {
        handle.join().unwrap();
    }
    println!("Result: {}", *counter.lock().unwrap());
}
```
標準で `Arc<T>`を使うと並列実行不要なコードでは、アトミック性の保証が不要なのにその保証処理が入りパフォーマンスに影響を及ぼす。そのため、`Arc<T>`は並列処理かつ複数スレッドで所有権を共有するときだけに使う。

## `Sync`と`Send`を使った並行性の拡張

# Rustのオブジェクト指向プログラミング
Rustは、オブジェクトとメソッド、カプセル化をサポートしているのが以前までの解説で分かる。

カプセル化は、 `pub`を使うことで公開APIにすることで実現している。

継承では、しばしば親クラスからサブクラスへ機能を共有過多になる。そのため、トレイトオブジェクトを活用するのが良い。

トレイトオブジェクトは、オブジェクト安全性が担保された状態しか担保しない。メソッドとしは、以下の特性を担保する。
- 戻り値の型が `self` でない
- ジェネリックな型引数がない

Rustには、OOP考案当初には無い所有権というアイデアがありそれを考慮した場合に、Rustで全てOOPに従った実装をすることがRustの強みを活かせない場合も有るためコードメンテナンス性も考慮して一部OOPのエッセンスを取り入れつつ所有権システムをうまく活用したRustらしいコード設計が求められる。


# パターンマッチング
`if let`, `match`などを活用した条件分岐とパターンマッチを作ることができる。

## `if let`パターン
`if let`を用いることで変数の代入と条件分岐を同時にできる。欠点としては、条件分岐の網羅性をコンパイラが保証できないところがあるその網羅性の担保は、`match`を活用すると良い。

## `for`ループ
pythonのように`enumerate`メソッドを持つため以下の様に配列とそのインデックスを取得できる。
```rust
let v = vec!['a', 'b', 'c'];

for (index, value) in v.iter().enumerate() {
    println!("{} is at index {}", value, index);
}
```

## `_`を使って未使用に変数を無視する
`_`を使うと変数を未使用でも警告が出ないようできる。

`_`変数での代入でも所有権が移動するため`_`のみ使って値を束縛することを阻止できる。
```rust
let s = Some(String::from("Hello!"));
if let Some(_) = s { // Some(_s)だとエラーになる
    println!("found a string")
} 

println!("{:?}", s);
```

## `ref`を使ったパターンに参照を生成する

match文の中で変数代入を行うとエラーになる。参照を行うことで安全に参照だけ行うことができる。

```rust
let robot_name = Some(String::from("Bors"));

match robot_name {
    Some(ref name) => println!("Found a name: {}", name),
    None => (),
}

println!("robot_name is : {:?}", robot_name);
```

参照の生成は、 `ref mut`を行える。
```rust
let mut robot_name = Some(String::from("Bors"));

match robot_name {
    Some(ref mut name) => *name = String::from("Another name"),
    None => (),
}

println!("robot_name is : {:?}", robot_name);
```



# test tool

- https://nexte.st/

# Attributes
Rustには、 `#[]`という記法があり、これはAttributesと呼ばれる。
役割は、以下の通りである。
- **コンパイラへの指示**: 特定の警告を抑制する (`#[allow]`)。
- **機能の有効化**: テスト関数としてマークする (`#[test]`)。
- **コード生成**: 特定のトレイトの実装を自動生成する (`#[derive]`)。
- **条件付きコンパイル**: 特定のオペレーティングシステムでのみコードをコンパイルする (`#[cfg]`)。
- **リンケージ制御**: 関数名をエクスポート用に変更する (`#[no_mangle]`)


## #[derive(Debug)]
debugトレイトを構造体に付与してprintln!など出力結果でより読みやすい表示形式の追加などを行える。

以下、コード例
```rust
#[derive(Debug)]
struct Rectangle {
    width: u32,
    height: u32
}

fn main() {
    let rect1 = Rectangle {width: 30, height: 50};

    println!("rect1 is {:?}", rect1);
    println!("rect1 is {:#?}", rect1); // 要素ごとに改行してくれる
}
```

## #[derive(PartialEq)]
2値以上の値比較を行えるようにするときに使う。
これを構造体に付与することで、2値以上の `==`, `!=`など評価が行えるようになる。

```rust
#[derive(Debug, PartialEq)]
struct Point {
    x: i32,
    y: i32,
}

fn main() {
    let p1 = Point { x: 1, y: 2 };
    let p2 = Point { x: 1, y: 2 };
    let p3 = Point { x: 3, y: 4 };

    // Debug formatting
    println!("{:?}", p1); // Output: Point { x: 1, y: 2 }

    // PartialEq comparison
    assert_eq!(p1, p2); // This assertion passes
    assert_ne!(p1, p3); // This assertion passes
}
```



# Turbofishを使った型指定
参考: https://keens.github.io/blog/2019/12/03/rustnoturbofishworikaisuru/
型指定をするときに、`::<>` という構文を使った型指定を行うことができる

```rust
fn generics<T>(t: T) {
    // ...
}
```

これを呼び出すときはどうやって指定しましょう？直感的にはこうですよね？

```rust
generics<u8>(0)
```

しかしこれは構文エラーです。

```text
error: chained comparison operators require parentheses
 --> turbofish.rs:6:13
  |
6 |     generics<u8>(0);
  |             ^^^^^
  |
  = help: use `::<...>` instead of `<...>` if you meant to specify type arguments
  = help: or use `(...)` if you meant to specify fn arguments

error: aborting due to previous error
```

エラーメッセージにも書いてある通り、型を指定するときは名前と型パラメータの間に `::` を置く必要があります。

```rust
generics::<u8>(0)
```
