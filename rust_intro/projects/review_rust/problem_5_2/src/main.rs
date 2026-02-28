trait Summary {
    fn summary(&self) -> String;

    // デフォルト実装
    fn preview(&self) -> String {
        format!(
            "{}...",
            &self.summary().chars().take(50).collect::<String>()
        )
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
impl Summary for Article {
    fn summary(&self) -> String {
        format!("「{}」, by: {}", self.content, self.author)
    }
}

impl Summary for Tweet {
    fn summary(&self) -> String {
        format!(
            "「{}」, by: {}, likes: {}",
            self.content, self.username, self.likes
        )
    }
}

fn print_summary(item: &impl Summary) {
    println!("{}", item.preview());
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_output_article_summary() {
        let article: Article = Article {
            title: String::from("Rust入門"),
            author: String::from("author"),
            content: String::from("test"),
        };

        assert_eq!("「test」, by: author", article.summary());
    }

    #[test]
    fn test_output_tweet_summary() {
        let tweet: Tweet = Tweet {
            username: String::from("test_user"),
            content: String::from("content"),
            likes: 0,
        };

        assert_eq!("「content」, by: test_user, likes: 0", tweet.summary());
    }

    #[test]
    fn test_output_article_over_50_chars() {
        let article: Article = Article {
            title: String::from("Rust入門"),
            author: String::from("author"),
            content: String::from(
                "test test test test test test test test test test test test test",
            ),
        };

        assert_eq!(
            "「test test test test test test test test test test...",
            article.preview()
        );
    }

    #[test]
    fn test_output_tweet_over_50_chars() {
        let tweet: Tweet = Tweet {
            username: String::from("test_user"),
            content: String::from("content contentcontentcontentcontentcontentcontentcontentcontentcontentcontentcontentcontent"),
            likes: 0,
        };

        assert_eq!(
            "「content contentcontentcontentcontentcontentconten...",
            tweet.preview()
        );
    }
}
