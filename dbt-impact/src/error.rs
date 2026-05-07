use std::path::PathBuf;

#[derive(Debug, thiserror::Error)]
pub enum ImpactError {
    #[error("manifest.json が見つかりませんでした: {0}")]
    ManifestNotFound(PathBuf),

    #[error("manifest.json がパースが失敗しました: {0}")]
    ParseError(#[from] serde_json::Error),

    #[error("モデルが見つかりません")]
    ModelNotFound(String),
}
