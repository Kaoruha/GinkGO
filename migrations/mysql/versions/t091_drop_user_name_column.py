"""移除 MUser.name 冗余字段

name 是 username 的历史镜像列（22459ac4 初始建表时创建，94e647f7 重构后保留）。
username 和 display_name 已完全替代 name 的语义，代码库中无任何引用。

Revision ID: t091
Revises: t090
Create Date: 2026-06-09
"""

from alembic import op
from sqlalchemy import text

revision = 't091'
down_revision = 't090'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(text(
        "ALTER TABLE `users` DROP COLUMN `name`"
    ))


def downgrade() -> None:
    op.execute(text(
        "ALTER TABLE `users` ADD COLUMN `name` VARCHAR(128) NOT NULL DEFAULT '' "
        "COMMENT '用户名称（= username 镜像，历史遗留）'"
    ))
