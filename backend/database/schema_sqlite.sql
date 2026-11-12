-- SQLite Schema for Code Quality Analyzer
-- Compatible with SQLite 3.23+

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    description TEXT,
    language TEXT NOT NULL DEFAULT 'python',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    total_files INTEGER NOT NULL DEFAULT 0,
    total_loc INTEGER NOT NULL DEFAULT 0,
    total_issues INTEGER NOT NULL DEFAULT 0,
    maintainability_index REAL,
    cyclomatic_complexity REAL,
    pylint_score REAL,
    security_issues_count INTEGER NOT NULL DEFAULT 0,
    total_score REAL,
    grade TEXT,
    summary TEXT,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    tool TEXT NOT NULL,
    rule_code TEXT,
    severity TEXT NOT NULL DEFAULT 'medium',
    category TEXT NOT NULL DEFAULT 'quality',
    file_path TEXT NOT NULL,
    line_number INTEGER,
    column_number INTEGER,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scoring_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_key TEXT NOT NULL UNIQUE,
    metric_name TEXT NOT NULL,
    weight REAL NOT NULL,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Seed default scoring configuration weights (total = 100%)
INSERT OR IGNORE INTO scoring_config (metric_key, metric_name, weight, description, is_active) VALUES
    ('pylint', 'Pylint Code Quality', 30.00, 'Điểm chuẩn mã nguồn và phát hiện lỗi tĩnh từ Pylint', 1),
    ('radon_mi', 'Maintainability Index', 25.00, 'Chỉ số khả năng bảo trì mã nguồn từ Radon', 1),
    ('radon_cc', 'Cyclomatic Complexity', 15.00, 'Độ phức tạp vòng lặp trung bình từ Radon', 1),
    ('bandit', 'Security Analysis (Bandit)', 20.00, 'Điểm an toàn mã nguồn Python từ Bandit', 1),
    ('pip_audit', 'Dependency Audit', 10.00, 'Kiểm tra lỗ hổng thư viện phụ thuộc từ pip-audit', 1);

