"""拆分 order.frozen 为 frozen_money + frozen_volume

order 表原有 frozen(DECIMAL) 字段只记录冻结金额，丢失了冻结数量。
拆为 frozen_money(DECIMAL) + frozen_volume(INT)，与 Entity 层 Order 对齐。

Revision ID: t090
Revises: t089
Create Date: 2026-06-07
"""

from alembic import op
from sqlalchemy import text

revision = 't090'
down_revision = 't089'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 添加新列
    op.execute(text(
        "ALTER TABLE `order` ADD COLUMN frozen_money DECIMAL(16,2) DEFAULT 0 COMMENT '冻结资金'"
    ))
    op.execute(text(
        "ALTER TABLE `order` ADD COLUMN frozen_volume INT DEFAULT 0 COMMENT '冻结数量'"
    ))
    # 2. 迁移旧数据：将 frozen 值复制到 frozen_money
    op.execute(text(
        "UPDATE `order` SET frozen_money = frozen WHERE frozen IS NOT NULL"
    ))
    # 3. 删除旧列
    op.execute(text(
        "ALTER TABLE `order` DROP COLUMN frozen"
    ))


def downgrade() -> None:
    # 1. 恢复旧列
    op.execute(text(
        "ALTER TABLE `order` ADD COLUMN frozen DECIMAL(16,2) DEFAULT 0 COMMENT '冻结金额(已废弃)'"
    ))
    # 2. 迁移数据：frozen_money 复制回 frozen
    op.execute(text(
        "UPDATE `order` SET frozen = frozen_money WHERE frozen_money IS NOT NULL"
    ))
    # 3. 删除新列
    op.execute(text(
        "ALTER TABLE `order` DROP COLUMN frozen_money"
    ))
    op.execute(text(
        "ALTER TABLE `order` DROP COLUMN frozen_volume"
    ))
