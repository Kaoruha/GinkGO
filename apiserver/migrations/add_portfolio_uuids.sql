-- 添加多 Portfolio 支持到回测任务表
-- 修改 portfolio_uuid 为可空（兼容旧数据）
-- 新增 portfolio_uuids 字段存储多个 Portfolio UUID

-- 1. 修改 portfolio_uuid 为可空
ALTER TABLE backtest_tasks MODIFY COLUMN portfolio_uuid VARCHAR(64) NULL;

-- 2. 添加 portfolio_uuids 字段
ALTER TABLE backtest_tasks ADD COLUMN portfolio_uuids TEXT NULL COMMENT '多投资组合UUID列表（JSON数组）' AFTER portfolio_name;

-- 3. 为现有数据迁移：将单个 portfolio_uuid 复制到 portfolio_uuids
UPDATE backtest_tasks
SET portfolio_uuids = JSON_ARRAY(portfolio_uuid)
WHERE portfolio_uuid IS NOT NULL AND portfolio_uuids IS NULL;
