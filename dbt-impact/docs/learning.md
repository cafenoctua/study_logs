# dbt-impact 学習まとめ

## 章構成

1. [serde によるデシリアライズ](#1-serde-によるデシリアライズ)
2. [pub と可視性](#2-pub-と可視性)
3. [Result と ? 演算子](#3-result-と--演算子)
4. [BFS（幅優先探索）](#4-bfs幅優先探索)
5. [イテレータ](#5-イテレータ)
6. [トレイト](#6-トレイト)
7. [メモリ管理（所有権・借用・Box）](#7-メモリ管理所有権借用box)
8. [参照と deref（*）](#8-参照と-deref)

---

## 1. serde によるデシリアライズ

### 学習ポイント

- `#[derive(Deserialize)]` を付けることで JSON → 構造体の変換が自動化される
- 構造体に定義していないフィールドは serde_json がデフォルトで無視する
- `serde_json::from_reader` はファイルをストリームとして読むためメモリ効率が良い

```rust
#[derive(Debug, Deserialize)]
pub struct Node {
    pub unique_id: String,
    pub name: String,
    pub resource_type: String,
    // JSON に他のフィールドがあっても無視される
}
```

### 確認問題

**Q1.** `#[derive(Deserialize)]` を付け忘れた場合、どのタイミングでエラーになりますか？

**Q2.** `serde_json::from_reader` と `serde_json::from_str` の違いは何ですか？どちらが大きなファイルに向いていますか？

**Q3.** JSON のキー名が `resource_type` で、Rust の構造体フィールド名を `resourceType` にしたい場合どうしますか？

---

## 2. pub と可視性

### 学習ポイント

- 構造体を `pub` にしても、フィールドはデフォルトで非公開
- フィールドを外部から読むには各フィールドに個別に `pub` が必要
- `impl` ブロックのメソッドも `pub` を付けないと外部から呼べない

```rust
pub struct Manifest {       // 構造体自体を公開
    pub nodes: HashMap<String, Node>,   // フィールドも個別に公開
    pub parent_map: HashMap<String, Vec<String>>,
}

impl Manifest {
    pub fn load(path: &Path) -> Result<Manifest, ...> { ... }  // メソッドも公開
}
```

### 確認問題

**Q1.** `pub struct Foo { bar: i32 }` と定義した場合、別モジュールから `foo.bar` にアクセスできますか？

**Q2.** `pub` を付けずに定義した関数は、同じファイル内からは呼べますか？

**Q3.** `pub(crate)` と `pub` の違いは何ですか？

---

## 3. Result と ? 演算子

### 学習ポイント

- `Result<T, E>` は成功（`Ok(T)`）か失敗（`Err(E)`）を表す型
- `?` 演算子は `Ok` なら中身を取り出し、`Err` なら即座に呼び出し元に返す
- `Box<dyn std::error::Error>` で複数種類のエラー型をまとめて扱える

```rust
pub fn load(path: &Path) -> Result<Manifest, Box<dyn std::error::Error>> {
    let file = std::fs::File::open(path)?;        // io::Error を伝播
    let manifest = serde_json::from_reader(file)?; // serde_json::Error を伝播
    Ok(manifest)
}
```

### 確認問題

**Q1.** `?` 演算子が使えるのはどのような関数の中だけですか？

**Q2.** `.unwrap()` と `?` の違いは何ですか？本番コードでどちらを使うべきですか？

**Q3.** `File::open` が返す型は何ですか？`?` を付けた後の型は何になりますか？

---

## 4. BFS（幅優先探索）

### 学習ポイント

- `VecDeque` をキューとして使い、先頭から取り出す（`pop_front`）・末尾に追加する（`push_back`）
- `HashSet` で訪問済みを管理し、無限ループを防ぐ
- `while let Some(x) = queue.pop_front()` でキューが空になるまで繰り返す
- `depth` は `Option<usize>` で受け取り、`None` なら制限なし・`Some(n)` なら深さ n まで

```rust
while let Some((node, d)) = queue.pop_front() {
    if visited.contains(&node) { continue; }
    visited.insert(node.clone());
    result.push((node.clone(), d));

    if let Some(max) = depth {
        if d >= max { continue; }  // 子をキューに積まない
    }

    if let Some(children) = map.get(&node) {
        for child in children {
            queue.push_back((child.clone(), d + 1));
        }
    }
}
```

### 確認問題

**Q1.** BFS と DFS の違いは何ですか？今回 BFS を選んだ理由は何だと思いますか？

**Q2.** `visited` の `HashSet` がなかった場合、どのような問題が起きますか？

**Q3.** `depth` で `break` でなく `continue` を使う理由は何ですか？

---

## 5. イテレータ

### 学習ポイント

- `iter()` で参照のイテレータを作り、`map` / `filter` / `find` などで変換・絞り込みができる
- `enumerate()` でインデックスと値のペア `(i, value)` を取得できる
- `take_while` は条件が偽になった時点で打ち切るイテレータ
- `collect::<Vec<_>>()` でイテレータを `Vec` に変換する
- `find` は条件に合う最初の要素を `Option` で返す

```rust
// enumerate でインデックス取得
for (i, (id, depth)) in nodes.iter().enumerate() { ... }

// find でモデル名を解決
nodes.keys().find(|k| k.ends_with(&format!(".{}", name))).cloned()

// take_while でスコープを限定
nodes[i+1..].iter().take_while(|(_, d)| *d >= *depth).any(...)
```

### 確認問題

**Q1.** `iter()` と `into_iter()` の違いは何ですか？

**Q2.** `filter().next()` と `find()` は同じ結果になりますか？

**Q3.** `collect::<Vec<_>>()` の `_` は何を意味していますか？

---

## 6. トレイト

### 学習ポイント

- トレイトは「このメソッドを持つ」という契約（インターフェース）を定義する
- `impl Trait for Type` で各型に独自の実装を与える
- `Box<dyn Trait>` でトレイトオブジェクトとして扱うと、複数の型を同じ変数に入れられる
- vtable を経由して実行時にどのメソッドを呼ぶか決定する（動的ディスパッチ）

```rust
pub trait Formatter {
    fn format(&self, root: &str, nodes: &[(String, usize)]) -> String;
}

// 呼び出し側は型を意識しない
let formatter: Box<dyn Formatter> = match format.as_str() {
    "tree" => Box::new(TreeFormatter),
    "json" => Box::new(JsonFormatter),
    _      => Box::new(ListFormatter),
};
formatter.format(&model, &result);
```

### 確認問題

**Q1.** トレイトオブジェクト（`Box<dyn Trait>`）とジェネリクス（`<T: Trait>`）の使い分けはどうすればよいですか？

**Q2.** `#[derive(Debug)]` も一種のトレイト実装です。自分で `impl Debug for Foo` を書くことはできますか？

**Q3.** 今回 `Formatter` トレイトを使ったことで、新しいフォーマット（例: CSV）を追加する場合に `main.rs` を変更する必要はありますか？

---

## 7. メモリ管理（所有権・借用・Box）

### 学習ポイント

- 値は必ず1つの変数だけが所有する（所有権）
- 所有者がスコープを抜けると自動でメモリが解放される（GC不要）
- `&T` で借用すると所有権を移さずに参照できる
- `Box<T>` でヒープに値を置き、ポインタ（固定サイズ）としてスタックで管理する
- `clone()` で所有権を移さずにコピーを作れる（`Clone` トレイトが必要）

```rust
// 所有権のムーブ
let a = String::from("hello");
let b = a;           // 所有権がbに移動
// println!("{}", a) // ❌ aは無効

// 借用
let s = String::from("hello");
let len = calc(&s);  // 借用（所有権は移らない）
println!("{}", s);   // ✅ sはまだ有効

// Box でヒープに置く
let b: Box<dyn Formatter> = Box::new(TreeFormatter);
// bがスコープを抜けるとヒープ上のTreeFormatterも自動解放
```

### 確認問題

**Q1.** `clone()` を使うとパフォーマンスに影響が出る場合があります。どのような場合に `clone()` を避けて借用を使うべきですか？

**Q2.** `Box<T>` を使わずに `dyn Trait` を変数に直接代入できない理由は何ですか？

**Q3.** Rustに GC（ガベージコレクション）が不要な理由を所有権の観点から説明してください。

---

## 8. 参照と deref（*）

### 学習ポイント

- `iter()` のループ変数は参照（`&T`）になる
- `*` デリファレンス演算子で参照から値を取り出す
- 数値の比較・演算では自動デリファレンスが効かないため `*depth` のように明示が必要
- `&String` は多くの場面で自動的に `&str` として扱われる（Deref強制）

```rust
for (i, (id, depth)) in nodes.iter().enumerate() {
    // id    の型: &String
    // depth の型: &usize

    if d + 1 == *depth { ... }  // *で値を取り出して比較
}
```

### 確認問題

**Q1.** `*` を付けないと比較できない場合と、付けなくても動く場合の違いは何ですか？

**Q2.** `&String` と `&str` の関係を説明してください。なぜ `&String` を `&str` として渡せるのですか？

**Q3.** 以下のコードで `*` が必要な箇所はどこですか？
```rust
let v: Vec<i32> = vec![1, 2, 3];
for x in v.iter() {
    println!("{}", x + 1);  // *x + 1 が必要？
}
```
