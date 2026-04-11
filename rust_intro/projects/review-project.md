# Rust学習まとめと復習課題

## 学習した内容のまとめ

### 1. 基礎 (hello_world, hello_cargo, variables, functions)

- **Hello World**: `println!`マクロによる出力
- **Cargo**: Rustのビルドシステム兼パッケージマネージャ
  - `cargo new`: プロジェクト作成
  - `cargo build`: ビルド
  - `cargo run`: ビルド＆実行
  - `cargo check`: コンパイルチェック
- **変数**:
  - `let`による不変変数、`let mut`による可変変数
  - `const`による定数定義
  - シャドーイング（同名変数の再定義）
  - データ型: 整数型、浮動小数点型、論理値型、文字型、タプル、配列
- **関数**:
  - `fn`キーワードによる定義
  - 引数の型注釈は必須
  - 戻り値は`->`で型を指定、最後の式（セミコロンなし）が戻り値

### 2. 制御フロー (if_statement, guessing_game)

- **if式**: 条件分岐、`if let`による簡潔な記述
- **ループ**: `loop`, `while`, `for`
- **ループラベル**: `'label:`で名前付きループ、`break 'label`で指定ループを脱出
- **match式**: パターンマッチング、網羅性チェック

### 3. 所有権システム (ownership)

- **所有権の3つの規則**:
  1. Rustの各値は所有者と呼ばれる変数を持つ
  2. 所有者は一度に1つだけ
  3. 所有者がスコープを抜けると値は破棄される
- **ムーブとコピー**: `String`はムーブ、プリミティブ型はコピー
- **参照と借用**: `&`による参照、`&mut`による可変参照
- **スライス**: `&s[start..end]`で部分参照

### 4. 構造体とメソッド (data_type_struct, method_maner)

- **構造体定義**: `struct`キーワード
- **デバッグ出力**: `#[derive(Debug)]`と`{:?}`または`{:#?}`
- **メソッド定義**: `impl`ブロック内で`&self`を第一引数に取る関数
- **関連関数**: `self`を取らない関数（`String::from()`のような）

### 5. 列挙型とパターンマッチ (enum_pattern_match, match_ope, if_let)

- **enum定義**: 複数のバリアントを持つ型
- **Option<T>**: 値の有無を表す（`Some(T)`または`None`）
- **match式**: 全パターンを網羅する必要あり、`_`でその他
- **if let**: 1つのパターンのみマッチする簡潔な記法

### 6. モジュールシステム (restaurant)

- **モジュール**: `mod`キーワードで定義
- **可視性**: デフォルトは非公開、`pub`で公開
- **パス**: `crate::`（絶対パス）、`self::`（相対パス）、`super::`（親モジュール）
- **use**: パスの省略、`as`でエイリアス

### 7. コレクション (collection)

- **ベクタ** (`Vec<T>`):
  - `Vec::new()`または`vec![]`で作成
  - `push`で追加、インデックスまたは`get`でアクセス
- **文字列** (`String`):
  - `String::from()`または`.to_string()`で作成
  - `push_str`で追加、`+`または`format!`で結合
  - UTF-8エンコード、インデックスアクセス不可
- **ハッシュマップ** (`HashMap<K, V>`):
  - `HashMap::new()`で作成
  - `insert`で追加、`get`で取得
  - `entry().or_insert()`で条件付き挿入

### 8. エラー処理 (error_processing)

- **panic!**: 回復不能なエラー
- **Result<T, E>**: 回復可能なエラー
- **?演算子**: エラーの委譲を簡潔に記述
- **unwrap/expect**: 簡易的なエラー処理（テスト向け）

### 9. ジェネリクス・トレイト・ライフタイム (generic_trait_lifetime)

- **ジェネリクス**: `<T>`で型パラメータを定義
- **トレイト**: 共通の振る舞いを定義（インターフェース的）
  - `impl Trait for Type`で実装
  - デフォルト実装可能
- **トレイト境界**: `T: Trait`で型制約
- **ライフタイム**: `'a`で参照の有効期間を指定

### 10. テスト (test_code, adder)

- **テスト関数**: `#[test]`属性
- **テストモジュール**: `#[cfg(test)]`でビルド時除外
- **アサーション**: `assert!`, `assert_eq!`, `assert_ne!`
- **結合テスト**: `tests/`ディレクトリ
- **Result型テスト**: `Ok(())`または`Err()`を返す

### 11. クロージャとイテレータ (closure_iterator)

- **クロージャ**: `|args| expression`で匿名関数
- **Fn系トレイト**: `Fn`, `FnMut`, `FnOnce`
- **イテレータ**: `iter()`, `into_iter()`, `iter_mut()`
- **イテレータアダプタ**: `map`, `filter`, `collect`など
- **消費メソッド**: `sum`, `collect`など

### 12. スマートポインタ (smartpointer)

- **Box<T>**: ヒープにデータを格納
- **Rc<T>**: 参照カウント（複数所有者）
- **RefCell<T>**: 内部可変性パターン
- **Derefトレイト**: 参照外しのカスタマイズ
- **Dropトレイト**: スコープ終了時の処理

### 13. 並行処理 (parallelism)

- **スレッド**: `thread::spawn`で生成
- **JoinHandle**: `join()`でスレッド終了待ち
- **moveクロージャ**: スレッドに所有権を移動
- **チャネル** (mpsc): スレッド間メッセージング
- **Mutex**: 排他制御
- **Arc<T>**: スレッドセーフな参照カウント

### 14. OOP的パターン (oop)

- **カプセル化**: `pub`による公開制御
- **トレイトオブジェクト**: 動的ディスパッチ
- **状態パターン**: enumまたはトレイトで実装

### 15. パターンマッチング詳細 (pattern_matching)

- **構造体の分解**: `let Point { x, y } = p;`
- **タプルの分解**: `let (a, b, c) = tuple;`
- **アンダースコア**: `_`で値を無視
- **ref/ref mut**: パターン内で参照を生成
- **ガード条件**: `if`句で追加条件

### 16. 実践プロジェクト (minigrep, calcuration, counting_up)

- **コマンドライン引数**: `std::env::args()`
- **ファイル読み込み**: `std::fs::File`
- **エラー型の定義**: カスタムenum
- **モジュール分割**: 機能ごとにファイル分け

---

## 復習課題

### Level 1: 基礎 (変数・関数・制御フロー)

#### 課題 1-1: 温度変換プログラム

摂氏から華氏、華氏から摂氏への変換関数を作成してください。

```rust
// ヒント: 華氏 = 摂氏 * 9/5 + 32

fn celsius_to_fahrenheit(celsius: f64) -> f64 {
    // TODO: 実装してください
}

fn fahrenheit_to_celsius(fahrenheit: f64) -> f64 {
    // TODO: 実装してください
}

fn main() {
    let c = 25.0;
    println!("{}°C = {}°F", c, celsius_to_fahrenheit(c));

   a  let f = 77.0;
    println!("{}°F = {}°C", f, fahrenheit_to_celsius(f));
}
```

#### 課題 1-2: FizzBuzz

1から30までの数を出力し、3の倍数なら"Fizz"、5の倍数なら"Buzz"、両方の倍数なら"FizzBuzz"を出力してください。

```rust
fn main() {
    // TODO: forループを使って実装してください
}
```

#### 課題 1-3: 配列の最大値

配列から最大値を見つける関数を実装してください。

```rust
fn find_max(numbers: &[i32]) -> i32 {
    // TODO: 実装してください
}

fn main() {
    let numbers = [34, 50, 25, 100, 65];
    println!("最大値: {}", find_max(&numbers));
}
```

---

### Level 2: 所有権と参照

#### 課題 2-1: 文字列の単語数カウント

文字列中の単語数をカウントする関数を作成してください（所有権を奪わない）。

```rust
fn count_words(s: &str) -> usize {
    // TODO: 実装してください
    // ヒント: split_whitespace()を使う
}

fn main() {
    let text = String::from("Hello Rust world");
    let count = count_words(&text);
    println!("単語数: {}", count);
    println!("元の文字列: {}", text); // textがまだ使える
}
```

#### 課題 2-2: 最長の文字列を返す

2つの文字列スライスを受け取り、長い方を返す関数を実装してください。

```rust
fn longest<'a>(s1: &'a str, s2: &'a str) -> &'a str {
    // TODO: 実装してください
}

fn main() {
    let s1 = String::from("short");
    let s2 = String::from("longer string");
    println!("長い方: {}", longest(&s1, &s2));
}
```

#### 課題 2-3: 文字列の一部を変更

可変参照を使って、文字列の末尾に感嘆符を追加する関数を作成してください。

```rust
fn add_excitement(s: &mut String) {
    // TODO: 実装してください
}

fn main() {
    let mut message = String::from("Hello");
    add_excitement(&mut message);
    println!("{}", message); // "Hello!"
}
```

---

### Level 3: 構造体とenum

#### 課題 3-1: 長方形構造体

長方形を表す構造体と、面積・周囲長を計算するメソッドを実装してください。

```rust
#[derive(Debug)]
struct Rectangle {
    // TODO: フィールドを定義
}

impl Rectangle {
    fn new(width: u32, height: u32) -> Self {
        // TODO: 実装
    }

    fn area(&self) -> u32 {
        // TODO: 実装
    }

    fn perimeter(&self) -> u32 {
        // TODO: 実装
    }

    fn is_square(&self) -> bool {
        // TODO: 実装
    }
}

fn main() {
    let rect = Rectangle::new(10, 20);
    println!("長方形: {:?}", rect);
    println!("面積: {}", rect.area());
    println!("周囲長: {}", rect.perimeter());
    println!("正方形か: {}", rect.is_square());
}
```

#### 課題 3-2: 計算機enum

四則演算を表すenumと、計算を実行するメソッドを実装してください。

```rust
enum Operation {
    Add,
    Subtract,
    Multiply,
    Divide,
}

impl Operation {
    fn calculate(&self, a: i32, b: i32) -> Option<i32> {
        // TODO: 実装（0除算はNoneを返す）
    }
}

fn main() {
    let ops = [
        (Operation::Add, 10, 5),
        (Operation::Subtract, 10, 5),
        (Operation::Multiply, 10, 5),
        (Operation::Divide, 10, 5),
        (Operation::Divide, 10, 0),
    ];

    for (op, a, b) in ops {
        match op.calculate(a, b) {
            Some(result) => println!("結果: {}", result),
            None => println!("計算エラー"),
        }
    }
}
```

#### 課題 3-3: メッセージ処理システム

異なる種類のメッセージを処理するenumを実装してください。

```rust
enum Message {
    Text(String),
    Number(i32),
    Quit,
}

impl Message {
    fn process(&self) {
        // TODO: メッセージの種類に応じて処理
        // Text: 文字列を出力
        // Number: 数値を2倍して出力
        // Quit: "終了します"と出力
    }
}

fn main() {
    let messages = vec![
        Message::Text(String::from("こんにちは")),
        Message::Number(42),
        Message::Quit,
    ];

    for msg in messages {
        msg.process();
    }
}
```

---

### Level 4: コレクションとエラー処理

#### 課題 4-1: 成績管理システム

学生の成績を管理するHashMapを使ったプログラムを作成してください。

```rust
use std::collections::HashMap;

fn main() {
    let mut scores: HashMap<String, Vec<u32>> = HashMap::new();

    // TODO: 以下の機能を実装
    // 1. 学生と点数を追加する関数
    // 2. 学生の平均点を計算する関数
    // 3. 全学生の成績を表示する関数

    // サンプルデータ
    // 田中: 80, 90, 85
    // 鈴木: 70, 75, 80
    // 佐藤: 95, 100, 90
}
```

#### 課題 4-2: ファイル読み込みとエラー処理

ファイルを読み込んで行数をカウントする関数を実装してください。

```rust
use std::fs::File;
use std::io::{self, BufRead, BufReader};

fn count_lines(filename: &str) -> Result<usize, io::Error> {
    // TODO: 実装
    // ヒント: File::open(), BufReader, lines()を使用
}

fn main() {
    match count_lines("test.txt") {
        Ok(count) => println!("行数: {}", count),
        Err(e) => println!("エラー: {}", e),
    }
}
```

#### 課題 4-3: カスタムエラー型

パスワード検証のカスタムエラー型を作成してください。

```rust
use std::fmt;

#[derive(Debug)]
enum PasswordError {
    TooShort(usize),      // 現在の長さを含む
    NoUppercase,
    NoLowercase,
    NoDigit,
}

impl fmt::Display for PasswordError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // TODO: エラーメッセージを実装
    }
}

fn validate_password(password: &str) -> Result<(), PasswordError> {
    // TODO: 実装
    // 条件: 8文字以上、大文字・小文字・数字を含む
}

fn main() {
    let passwords = ["short", "alllowercase", "ALLUPPERCASE", "NoDigits", "Valid1Pass"];

    for pw in passwords {
        match validate_password(pw) {
            Ok(()) => println!("{}: OK", pw),
            Err(e) => println!("{}: {}", pw, e),
        }
    }
}
```

---

### Level 5: ジェネリクスとトレイト

#### 課題 5-1: スタック実装

ジェネリクスを使ったスタックを実装してください。

```rust
struct Stack<T> {
    items: Vec<T>,
}

impl<T> Stack<T> {
    fn new() -> Self {
        // TODO
    }

    fn push(&mut self, item: T) {
        // TODO
    }

    fn pop(&mut self) -> Option<T> {
        // TODO
    }

    fn peek(&self) -> Option<&T> {
        // TODO
    }

    fn is_empty(&self) -> bool {
        // TODO
    }

    fn len(&self) -> usize {
        // TODO
    }
}

fn main() {
    let mut stack: Stack<i32> = Stack::new();
    stack.push(1);
    stack.push(2);
    stack.push(3);

    while let Some(value) = stack.pop() {
        println!("{}", value);
    }
}
```

#### 課題 5-2: Summaryトレイト

複数の型に共通の`summary`メソッドを持たせるトレイトを実装してください。

```rust
trait Summary {
    fn summary(&self) -> String;

    // デフォルト実装
    fn preview(&self) -> String {
        format!("{}...", &self.summary()[..50.min(self.summary().len())])
    }
}

struct Article {
    title: String,
    author: String,
    content: String,
}

struct Tweet {
    username: String,
    content: String,
    likes: u32,
}

// TODO: ArticleとTweetにSummaryを実装

fn print_summary(item: &impl Summary) {
    println!("{}", item.summary());
}

fn main() {
    let article = Article {
        title: String::from("Rust入門"),
        author: String::from("田中"),
        content: String::from("Rustは安全性と速度を両立したプログラミング言語です..."),
    };

    let tweet = Tweet {
        username: String::from("rustacean"),
        content: String::from("Rustを始めました！"),
        likes: 100,
    };

    print_summary(&article);
    print_summary(&tweet);
}
```

#### 課題 5-3: 比較可能なペア

2つの値を持ち、大きい方を返すメソッドを持つ構造体を実装してください。

```rust
use std::cmp::PartialOrd;

struct Pair<T> {
    first: T,
    second: T,
}

impl<T: PartialOrd> Pair<T> {
fn new(first: T, second: T) -> Self {
        // TODO
    }

    fn larger(&self) -> &T {
        // TODO
    }
}

fn main() {
    let int_pair = Pair::new(5, 10);
    println!("大きい方: {}", int_pair.larger());

    let str_pair = Pair::new("apple", "banana");
    println!("大きい方: {}", str_pair.larger());
}
```

---

### Level 6: イテレータとクロージャ

#### 課題 6-1: カスタムイテレータ

指定した範囲の偶数だけを生成するイテレータを実装してください。

```rust
struct EvenNumbers {
    current: u32,
    max: u32,
}

impl EvenNumbers {
    fn new(max: u32) -> Self {
        // TODO
    }
}

impl Iterator for EvenNumbers {
    type Item = u32;

    fn next(&mut self) -> Option<Self::Item> {
        // TODO
    }
}

fn main() {
    let evens = EvenNumbers::new(10);
    for n in evens {
        println!("{}", n);
    }
    // 出力: 2, 4, 6, 8, 10
}
```

#### 課題 6-2: イテレータメソッドチェーン

イテレータのメソッドチェーンを使って、以下の処理を1行で実装してください。

```rust
fn main() {
    let numbers = vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

    // TODO: 偶数だけをフィルタし、それぞれ2乗して、合計を求める
    // 結果: 2^2 + 4^2 + 6^2 + 8^2 + 10^2 = 220
    let result: i32 = numbers.iter()
        // ここにメソッドチェーンを追加
        ;

    println!("結果: {}", result);
}
```

#### 課題 6-3: クロージャを使ったキャッシュ

計算結果をキャッシュするクロージャラッパーを実装してください。

```rust
use std::collections::HashMap;

struct Cacher<T>
where
    T: Fn(u32) -> u32,
{
    calculation: T,
    values: HashMap<u32, u32>,
}

impl<T> Cacher<T>
where
    T: Fn(u32) -> u32,
{
    fn new(calculation: T) -> Self {
        // TODO
    }

    fn value(&mut self, arg: u32) -> u32 {
        // TODO: キャッシュがあれば返し、なければ計算してキャッシュ
    }
}

fn main() {
    let mut expensive_calculation = Cacher::new(|n| {
        println!("計算中... {}", n);
        n * n
    });

    println!("結果: {}", expensive_calculation.value(5)); // 計算される
    println!("結果: {}", expensive_calculation.value(5)); // キャッシュから
    println!("結果: {}", expensive_calculation.value(3)); // 計算される
}
```

---

### Level 7: 並行処理

#### 課題 7-1: 並列合計計算

配列を複数のスレッドで分割して合計を計算してください。

```rust
use std::sync::{Arc, Mutex};
use std::thread;

fn parallel_sum(numbers: Vec<i32>, num_threads: usize) -> i32 {
    // TODO: 実装
    // ヒント: Arc<Mutex<i32>>で共有状態を管理
    0
}

fn main() {
    let numbers: Vec<i32> = (1..=100).collect();
    let result = parallel_sum(numbers, 4);
    println!("合計: {}", result); // 5050
}
```

#### 課題 7-2: プロデューサー・コンシューマー

チャネルを使ったプロデューサー・コンシューマーパターンを実装してください。

```rust
use std::sync::mpsc;
use std::thread;
use std::time::Duration;

fn main() {
    // TODO: 実装
    // 1. 3つのプロデューサースレッドを作成
    // 2. 各プロデューサーは自分のIDと1〜5の数字を送信
    // 3. メインスレッドで全メッセージを受信して表示
}
```

#### 課題 7-3: スレッドプール的パターン

ワーカースレッドがタスクを処理するパターンを実装してください。

```rust
use std::sync::{Arc, Mutex, mpsc};
use std::thread;

fn main() {
    // TODO: 実装
    // 1. タスクキュー（チャネル）を作成
    // 2. 3つのワーカースレッドを起動
    // 3. 10個のタスク（数値の2乗を計算）をキューに投入
    // 4. 全ての結果を収集
}
```

---

### Level 8: 総合課題

#### 課題 8-1: TODOリスト管理CLIアプリ

コマンドライン引数でTODOを管理するアプリを作成してください。

要件:

- `add <title>`: TODOを追加
- `list`: 全TODOを表示
- `done <id>`: TODOを完了にする
- `remove <id>`: TODOを削除
- TODOはファイルに保存/読み込み

```rust
use std::env;
use std::fs;

#[derive(Debug)]
struct Todo {
    id: u32,
    title: String,
    completed: bool,
}

struct TodoList {
    todos: Vec<Todo>,
    next_id: u32,
}

impl TodoList {
    fn new() -> Self {
        // TODO: ファイルから読み込み
        TodoList {
            todos: Vec::new(),
            next_id: 1,
        }
    }

    fn add(&mut self, title: String) {
        // TODO
    }

    fn list(&self) {
        // TODO
    }

    fn complete(&mut self, id: u32) {
        // TODO
    }

    fn remove(&mut self, id: u32) {
        // TODO
    }

    fn save(&self) {
        // TODO: ファイルに保存
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    // TODO: コマンドライン引数を処理
}
```

#### 課題 8-2: 簡易HTTPクライアント風パーサー

HTTP風のレスポンスをパースするプログラムを作成してください。

```rust
use std::collections::HashMap;

#[derive(Debug)]
struct HttpResponse {
    status_code: u16,
    headers: HashMap<String, String>,
    body: String,
}

#[derive(Debug)]
enum ParseError {
    InvalidStatusLine,
    InvalidHeader,
    EmptyResponse,
}

impl HttpResponse {
    fn parse(response: &str) -> Result<Self, ParseError> {
        // TODO: 実装
        // 形式:
        // HTTP/.1 200 OK
        // Content-Type: text/plain
        // Content-Length: 13
        //
        // Hello, World!
        Err(ParseError::EmptyResponse)
    }
}

fn main() {
    let response = r#"HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 13

Hello, World!"#;

    match HttpResponse::parse(response) {
        Ok(resp) => {
            println!("Status: {}", resp.status_code);
            println!("Headers: {:?}", resp.headers);
            println!("Body: {}", resp.body);
        }
        Err(e) => println!("Parse error: {:?}", e),
    }
}
```

#### 課題 8-3: 式評価器の拡張

calculationプロジェクトを参考に、括弧付きの式を評価できるように拡張してください。

要件:

- 括弧 `()` をサポート
- 演算子の優先順位（`*` `/` は `+` `-` より優先）
- 例: `(1 + 2) * 3` = 9

```rust
// ヒント: 再帰下降パーサーまたはシャントingヤード・アルゴリズムを使用

#[derive(Debug)]
enum Token {
    Number(i32),
    Plus,
    Minus,
    Multiply,
    Divide,
    LeftParen,
    RightParen,
}

fn tokenize(input: &str) -> Result<Vec<Token>, String> {
    // TODO
    Ok(vec![])
}

fn evaluate(tokens: &[Token]) -> Result<i32, String> {
    // TODO
    Ok(0)
}

fn main() {
    let expressions = [
        "1 + 2 * 3",      // = 7
        "(1 + 2) * 3",    // = 9
        "10 - (3 + 2)",   // = 5
    ];

    for expr in expressions {
        match tokenize(expr).and_then(|tokens| evaluate(&tokens)) {
            Ok(result) => println!("{} = {}", expr, result),
            Err(e) => println!("{}: エラー - {}", expr, e),
        }
    }
}
```

---

## 解答のヒント

### Level 1-3: 解答例は標準的なRustの書き方を参照

- 公式ドキュメント: <https://doc.rust-jp.rs/book-ja/>

### Level 4以降: プロジェクト内のコードを参考に

- `minigrep`: エラー処理、ファイル操作
- `calcuration`: モジュール分割、カスタムエラー
- `closure_iterator`: イテレータ、クロージャ
- `parallelism`: 並行処理
- `oop`: トレイトオブジェクト

---

## 学習のポイント

1. **所有権を理解する**: Rust最大の特徴。コンパイルエラーを恐れず、エラーメッセージをよく読む
2. **小さく始める**: 最初からすべてを理解しようとせず、基本から積み上げる
3. **コンパイラを信頼する**: Rustのコンパイラは非常に親切。エラーメッセージに従う
4. **実際に書く**: 読むだけでなく、実際にコードを書いて動かすことが重要
5. **公式ドキュメントを活用**: Rustの公式ドキュメントは非常に充実している
