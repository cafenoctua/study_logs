# タスク一覧

## コンパイルエラーの修正（優先度: 高）

- [ ] `parse_expression`関数の完成（src/main.rs:60-61）
  - `if`文が途中で切れている
  - 数値の範囲チェック（-1000 〜 1000）を追加
  - 返り値の型を `Result<(Vec<i32>, Vec<Operator>), CalcError>` に修正

## スペルミスの修正

- [x] `calculator` → `calculator` に修正
- [x] `Subtract` → `Subtract` に修正
- [x] `subtract` → `subtract` に修正（関数名の一貫性）

## Rustらしい書き方への改善

### 1. `Operator`列挙型の活用
現状: `Operator`が定義されているが使われていない

```rust
// 改善案: Operatorにcalculateメソッドを追加
impl Operator {
    fn calculate(&self, a: i32, b: i32) -> Result<i32, CalcError> {
        match self {
            Operator::Add => Ok(a + b),
            Operator::Subtract => Ok(a - b),
            Operator::Multiply => Ok(a * b),
            Operator::Divide => {
                if b == 0 {
                    Err(CalcError::DivisionByZero)
                } else {
                    Ok(a / b)
                }
            }
        }
    }
}
```

これにより `add`, `subtract`, `multiply`, `division` 関数は不要になる。

### 2. イテレータの活用
現状の`parse_expression`は手続き的。イテレータを活用した書き方：

```rust
fn parse_expression(args: Vec<String>) -> Result<(Vec<i32>, Vec<Operator>), CalcError> {
    if args.len() < 3 || args.len() % 2 == 0 {
        return Err(CalcError::InvalidFormat);
    }

    let numbers: Result<Vec<i32>, CalcError> = args
        .iter()
        .step_by(2)
        .map(|s| {
            s.parse::<i32>()
                .map_err(|_| CalcError::InvalidNumber(s.clone()))
                .and_then(|n| {
                    if n < -1000 || n > 1000 {
                        Err(CalcError::NumberOutOfRange(n))
                    } else {
                        Ok(n)
                    }
                })
        })
        .collect();

    let operators: Result<Vec<Operator>, CalcError> = args
        .iter()
        .skip(1)
        .step_by(2)
        .map(|s| s.parse::<Operator>())
        .collect();

    Ok((numbers?, operators?))
}
```

### 3. `Display`トレイトの実装
エラーメッセージを人間が読みやすい形で出力するため：

```rust
use std::fmt;

impl fmt::Display for CalcError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CalcError::InsufficientArgs => write!(f, "引数が不足しています"),
            CalcError::InvalidNumber(s) => write!(f, "無効な数値: {}", s),
            CalcError::InvalidOperator(s) => write!(f, "無効な演算子: {}", s),
            CalcError::DivisionByZero => write!(f, "ゼロ除算エラー"),
            CalcError::NumberOutOfRange(n) => write!(f, "範囲外の数値: {} (-1000〜1000)", n),
            CalcError::InvalidFormat => write!(f, "入力形式が不正です"),
        }
    }
}
```

### 4. `calculator`関数の改善
`Result`型を返すように変更：

```rust
fn calculator(nums: Vec<i32>, operators: Vec<Operator>) -> Result<i32, CalcError> {
    let mut result = nums[0];

    for (num, op) in nums.iter().skip(1).zip(operators.iter()) {
        result = op.calculate(result, *num)?;
    }

    Ok(result)
}
```

### 5. `main`関数でのエラーハンドリング
`unwrap()`を避け、適切にエラーを処理：

```rust
fn main() {
    let args: Vec<String> = env::args().skip(1).collect();

    match run(args) {
        Ok(result) => println!("Result: {}", result),
        Err(e) => {
            eprintln!("Error: {}", e);
            std::process::exit(1);
        }
    }
}

fn run(args: Vec<String>) -> Result<i32, CalcError> {
    let (nums, operators) = parse_expression(args)?;
    calculator(nums, operators)
}
```

### 6. `Args`構造体の整理
現状: `args`フィールドが未使用、`new`と`parse_expression`が別々

改善案: 構造体を削除するか、以下のように統合：

```rust
struct Expression {
    numbers: Vec<i32>,
    operators: Vec<Operator>,
}

impl Expression {
    fn parse(args: Vec<String>) -> Result<Self, CalcError> {
        // パース処理
    }

    fn evaluate(&self) -> Result<i32, CalcError> {
        // 計算処理
    }
}
```

## 未実装のバリデーション（README.mdより）

- [ ] 入力値が `1 ++ 1` と不当な場合の判別
- [ ] 入力が `1 + 1 +` と演算式で終わる場合の判別
- [ ] 入力が `a b c` と不当な入力の判別
- [ ] 入力値に1000より大きい値が含まれる時のエラー
- [ ] 入力値に-1000より小さい値が含まれる時のエラー

## 追加で検討すべき機能

- [ ] ゼロ除算時のエラーハンドリング（`DivisionByZero`エラーは定義済みだが未使用）
- [ ] 出力値の範囲チェック（-1000000 〜 1000000）
- [ ] `std::error::Error`トレイトの実装
- [ ] 単体テストの追加（エラーケース用）

## ファイル構成の提案（将来的に）

現状は全て`main.rs`に記述されているが、以下のように分割することも検討：

```
src/
├── main.rs          # エントリーポイント
├── error.rs         # CalcError定義
├── operator.rs      # Operator列挙型
├── expression.rs    # パース処理
└── calculator.rs    # 計算処理
```
