"""run_id → task_id 全量统一

Revision ID: t089
Revises: a1b2c3d4e5f6
Create Date: 2026-04-24
"""

from alembic import op
from sqlalchemy import text

revision = 't089'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(text("ALTER TABLE backtest_task CHANGE COLUMN run_id task_id VARCHAR(32) NOT NULL COMMENT '任务ID（执行会话标识）'"))
    op.execute(text("ALTER TABLE engine CHANGE COLUMN current_run_id current_task_id VARCHAR(128) DEFAULT '' COMMENT '当前任务ID'"))
    op.execute(text("ALTER TABLE signal_tracker CHANGE COLUMN run_id task_id VARCHAR(32) DEFAULT '' COMMENT '任务ID'"))
    op.execute(text("ALTER TABLE `order` CHANGE COLUMN run_id task_id VARCHAR(32) DEFAULT '' COMMENT '任务ID'"))
    op.execute(text("ALTER TABLE position CHANGE COLUMN run_id task_id VARCHAR(32) DEFAULT '' COMMENT '任务ID'"))
    op.execute(text("ALTER TABLE transfer CHANGE COLUMN run_id task_id VARCHAR(32) DEFAULT '' COMMENT '任务ID'"))
    op.execute(text("ALTER TABLE run_record CHANGE COLUMN run_id task_id VARCHAR(32) DEFAULT '' COMMENT '任务ID'"))


def downgrade() -> None:
    op.execute(text("ALTER TABLE run_record CHANGE COLUMN task_id run_id VARCHAR(32) DEFAULT '' COMMENT '运行会话ID'"))
    op.execute(text("ALTER TABLE transfer CHANGE COLUMN task_id run_id VARCHAR(32) DEFAULT '' COMMENT '运行会话ID'"))
    op.execute(text("ALTER TABLE position CHANGE COLUMN task_id run_id VARCHAR(32) DEFAULT '' COMMENT '运行会话ID'"))
    op.execute(text("ALTER TABLE `order` CHANGE COLUMN task_id run_id VARCHAR(32) DEFAULT '' COMMENT '运行会话ID'"))
    op.execute(text("ALTER TABLE signal_tracker CHANGE COLUMN task_id run_id VARCHAR(32) DEFAULT '' COMMENT '运行会话ID'"))
    op.execute(text("ALTER TABLE engine CHANGE COLUMN current_task_id current_run_id VARCHAR(128) DEFAULT '' COMMENT '当前运行会话ID'"))
    op.execute(text("ALTER TABLE backtest_task CHANGE COLUMN task_id run_id VARCHAR(32) NOT NULL COMMENT '运行会话ID（统一标识）'"))
