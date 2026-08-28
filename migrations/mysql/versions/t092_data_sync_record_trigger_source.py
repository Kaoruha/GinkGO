"""data_sync_record 加 trigger_source 触发来源列

Revision ID: t092
Revises: t091
Create Date: 2026-08-18

数据同步异步化改造(Web/CLI 统一发 Kafka 由 data-worker 执行):同步历史需
区分触发来源——web=网页手动 / cli=ginkgo CLI / scheduled=tasktimer 定时,
枚举 TRIGGER_SOURCE_TYPES(0=other/1=web/2=cli/3=scheduled) int 入库,
对齐 source 列的枚举惯例。历史行无来源 → DEFAULT 0(other)。
"""

from alembic import op
from sqlalchemy import text

revision = 't092'
down_revision = 't091'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(text(
        "ALTER TABLE data_sync_record "
        "ADD COLUMN trigger_source TINYINT NOT NULL DEFAULT 0 "
        "COMMENT '触发来源: 0=other/1=web/2=cli/3=scheduled (TRIGGER_SOURCE_TYPES)'"
    ))


def downgrade() -> None:
    op.execute(text("ALTER TABLE data_sync_record DROP COLUMN trigger_source"))
