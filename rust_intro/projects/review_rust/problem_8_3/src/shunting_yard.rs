use crate::error::CalcError;
use crate::operator::Operator;

/// 数式の各要素を表すトークン型
#[derive(Debug, PartialEq, Clone)]
pub enum Token {
    Number(i32),
    Op(Operator),
    LeftParen,
    RightParen,
}

/// 文字列のスライスをトークン列に変換する
pub fn tokenize(args: &[String]) -> Result<Vec<Token>, CalcError> {
    args.iter()
        .map(|s| match s.as_str() {
            "(" => Ok(Token::LeftParen),
            ")" => Ok(Token::RightParen),
            "+" | "-" | "*" | "/" => Ok(Token::Op(s.parse::<Operator>()?)),
            _ => s
                .parse::<i32>()
                .map(Token::Number)
                .map_err(|_| CalcError::InvalidNumber(s.clone())),
        })
        .collect()
}

/// シャンティングヤードアルゴリズムで中置記法トークン列をRPN（後置記法）に変換する
///
/// # アルゴリズムの流れ
/// トークンを左から順に処理する：
/// - 数値 → 出力キューへ直接追加
/// - 演算子 → スタックの先頭と優先度を比較し、スタック先頭が同等以上なら先にpopして出力キューへ
/// - `(` → スタックへ積む
/// - `)` → `(` が現れるまでスタックをpopして出力キューへ
/// 最後にスタックの残りをすべて出力キューへ移す
pub fn to_rpn(tokens: Vec<Token>) -> Result<Vec<Token>, CalcError> {
    let mut output: Vec<Token> = Vec::new();
    let mut op_stack: Vec<Token> = Vec::new();

    // TODO(human): ここにシャンティングヤードのコアロジックを実装してください
    // tokens を for ループで処理し、上記のアルゴリズムの流れに従って
    // output と op_stack を操作してください。
    // 最後に op_stack の残りを output に移して Ok(output) を返します。

    for token in tokens {
        match token {
            Token::Number(_) => output.push(token),
            Token::Op(op) => {
                while let Some(top) = op_stack.last() {
                    match top {
                        Token::Op(top_op) if top_op.precedence() >= op.precedence() => {
                            output.push(op_stack.pop().unwrap());
                        }
                        _ => break,
                    }
                }
                op_stack.push(Token::Op(op));
            }
            Token::LeftParen => {
                op_stack.push(Token::LeftParen);
            }
            Token::RightParen => {
                let mut found = false;
                while let Some(top) = op_stack.last() {
                    if *top == Token::LeftParen {
                        op_stack.pop();
                        found = true;
                        break;
                    }
                    output.push(op_stack.pop().unwrap());
                }

                if !found {
                    return Err(CalcError::InvalidFormat);
                }
            }
        }
    }
    output.extend(op_stack.into_iter().rev());
    Ok(output)
}

/// RPN列を評価して結果を返す
pub fn evaluate_rpn(rpn: &[Token]) -> Result<i32, CalcError> {
    let mut stack: Vec<i32> = Vec::new();

    for token in rpn {
        match token {
            Token::Number(n) => stack.push(*n),
            Token::Op(op) => {
                let b = stack.pop().ok_or(CalcError::InvalidFormat)?;
                let a = stack.pop().ok_or(CalcError::InvalidFormat)?;
                stack.push(op.calculate(a, b)?);
            }
            _ => return Err(CalcError::InvalidFormat),
        }
    }

    stack.pop().ok_or(CalcError::InvalidFormat)
}
