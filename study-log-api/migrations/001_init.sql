CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path   TEXT    NOT NULL UNIQUE,
    title       TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    content     TEXT    NOT NULL,
    scanned_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS topics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    source_file TEXT    NOT NULL,
    completed   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date);
