CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    path VARCHAR(500) NOT NULL,
    description TEXT NULL,
    language VARCHAR(50) NOT NULL DEFAULT 'python',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS analysis_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    status ENUM('pending', 'running', 'completed', 'failed') NOT NULL DEFAULT 'pending',
    total_files INT NOT NULL DEFAULT 0,
    total_loc INT NOT NULL DEFAULT 0,
    total_issues INT NOT NULL DEFAULT 0,
    maintainability_index DECIMAL(5, 2) NULL,
    cyclomatic_complexity DECIMAL(6, 2) NULL,
    pylint_score DECIMAL(4, 2) NULL,
    security_issues_count INT NOT NULL DEFAULT 0,
    total_score DECIMAL(5, 2) NULL,
    grade VARCHAR(10) NULL,
    summary TEXT NULL,
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    CONSTRAINT fk_sessions_project
        FOREIGN KEY (project_id) REFERENCES projects(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS issues (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    tool VARCHAR(50) NOT NULL,
    rule_code VARCHAR(50) NULL,
    severity ENUM('info', 'low', 'medium', 'high', 'critical') NOT NULL DEFAULT 'medium',
    category VARCHAR(50) NOT NULL DEFAULT 'quality',
    file_path VARCHAR(500) NOT NULL,
    line_number INT NULL,
    column_number INT NULL,
    message TEXT NOT NULL,
    status ENUM('open', 'in_progress', 'fixed', 'ignored') NOT NULL DEFAULT 'open',
    note TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_issues_session
        FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS scoring_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metric_key VARCHAR(50) NOT NULL UNIQUE,
    metric_name VARCHAR(100) NOT NULL,
    weight DECIMAL(5, 2) NOT NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dữ liệu trọng số chấm điểm mặc định (tổng = 100%)
INSERT IGNORE INTO scoring_config (metric_key, metric_name, weight, description, is_active) VALUES
    ('pylint', 'Pylint Code Quality', 30.00, 'Điểm chuẩn mã nguồn và phát hiện lỗi tĩnh từ Pylint', TRUE),
    ('radon_mi', 'Maintainability Index', 25.00, 'Chỉ số khả năng bảo trì mã nguồn từ Radon', TRUE),
    ('radon_cc', 'Cyclomatic Complexity', 15.00, 'Độ phức tạp vòng lặp trung bình từ Radon', TRUE),
    ('bandit', 'Security Analysis (Bandit)', 20.00, 'Điểm an toàn mã nguồn Python từ Bandit', TRUE),
    ('pip_audit', 'Dependency Audit', 10.00, 'Kiểm tra lỗ hổng thư viện phụ thuộc từ pip-audit', TRUE);

