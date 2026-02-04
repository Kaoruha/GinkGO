-- 回测任务表
CREATE TABLE IF NOT EXISTS backtest_tasks (
    uuid VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    portfolio_uuid VARCHAR(64) NOT NULL,
    portfolio_name VARCHAR(255),
    state VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    progress FLOAT DEFAULT 0.0,
    config JSON,
    result JSON,
    worker_id VARCHAR(64),
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,

    INDEX idx_state (state),
    INDEX idx_portfolio (portfolio_uuid),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
