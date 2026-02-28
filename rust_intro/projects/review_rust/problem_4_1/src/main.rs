use std::{collections::HashMap, vec};

// 1. 学生と点数を追加する関数
fn input_sumple_data() -> HashMap<String, Vec<u32>> {
    let mut scores: HashMap<String, Vec<u32>> = HashMap::new();

    scores.insert("田中".to_string(), vec![80, 90, 85]);
    scores.insert("鈴木".to_string(), vec![70, 75, 80]);
    scores.insert("佐藤".to_string(), vec![95, 100, 90]);
    scores
}

// 2. 学生の平均点を計算する関数
fn calc_student_scores_avg(scores: &HashMap<String, Vec<u32>>) -> HashMap<String, Option<u32>> {
    let mut avg_scores: HashMap<String, Option<u32>> = HashMap::new();

    for (name, score) in scores.iter() {
        if score.is_empty() {
            avg_scores.insert(name.to_string(), None);
            continue;
        }

        let total_score: u32 = score.iter().sum();
        let score_length = score.len() as u32;
        avg_scores.insert(name.to_string(), Some(total_score / score_length));
    }

    avg_scores
}

// 3. 全学生の成績を表示する関数
fn disply_student_grades(grades: HashMap<String, Option<u32>>) {
    for (name, score) in grades.iter() {
        match score {
            Some(s) => println!("成績: {} 平均点: {}", name, s),
            None => println!("成績: {} 平均点: データなし", name),
        }
    }
}

fn main() {
    // TODO: 以下の機能を実装

    // サンプルデータ
    // 田中: 80, 90, 85
    // 鈴木: 70, 75, 80
    // 佐藤: 95, 100, 90
    //
    let scores = input_sumple_data();

    let avg_scores = calc_student_scores_avg(&scores);

    disply_student_grades(avg_scores);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_all_score_10_avg() {
        let mut scores = HashMap::new();
        scores.insert("test".to_string(), vec![10, 10, 10]);

        let mut correct_result: HashMap<String, Option<u32>> = HashMap::new();
        correct_result.insert("test".to_string(), Some(10));

        assert_eq!(correct_result, calc_student_scores_avg(&scores));
    }

    #[test]
    fn test_2score_avg() {
        let mut scores = HashMap::new();
        scores.insert("test".to_string(), vec![10, 0]);

        let mut correct_result: HashMap<String, Option<u32>> = HashMap::new();
        correct_result.insert("test".to_string(), Some(5));

        assert_eq!(correct_result, calc_student_scores_avg(&scores));
    }

    #[test]
    fn test_all_score_0_avg() {
        let mut scores = HashMap::new();
        scores.insert("test".to_string(), vec![0, 0]);

        let mut correct_result: HashMap<String, Option<u32>> = HashMap::new();
        correct_result.insert("test".to_string(), Some(0));

        assert_eq!(correct_result, calc_student_scores_avg(&scores));
    }

    #[test]
    fn test_score_brank_avg() {
        let mut scores = HashMap::new();
        scores.insert("test".to_string(), vec![]);

        let mut correct_result: HashMap<String, Option<u32>> = HashMap::new();
        correct_result.insert("test".to_string(), None);

        assert_eq!(correct_result, calc_student_scores_avg(&scores));
    }
}
