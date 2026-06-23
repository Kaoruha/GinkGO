"""add deployment and user_credentials tables

Revision ID: 84a2de8c7c00
Revises: 0336f9b2c8a2, t088_trade_records
Create Date: 2026-03-30 10:59:58.419459

Merge node: 收敛 0336f9b2c8a2 (extend_models_for_live_trading) 与
t088_trade_records 两条分支（两者 down_revision 均为 0245d8e3a9f1）。
此前该文件仅存在于未合并的 feature 分支，master 缺失导致 a1b2c3d4e5f6
的 down_revision='84a2de8c7c00' 悬空、alembic upgrade head 报 multiple heads (#5529)。

user_credentials 表镜像 MUserCredential(model_user_credential.py)：user_id
外键指向 users.uuid（users 表由 create_all 建立，属项目 create_all + alembic
混合建表惯例）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84a2de8c7c00'
down_revision: Union[str, Sequence[str], None] = ('0336f9b2c8a2', 't088_trade_records')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'deployment',
        sa.Column('uuid', sa.String(32), primary_key=True),
        sa.Column('source_task_id', sa.String(32), server_default='', comment='回测任务ID'),
        sa.Column('target_portfolio_id', sa.String(32), server_default='', comment='部署后的Portfolio ID'),
        sa.Column('source_portfolio_id', sa.String(32), server_default='', comment='原始回测Portfolio ID'),
        sa.Column('mode', sa.Integer(), server_default='-1', comment='运行模式: 0=回测, 1=纸上交易, 2=实盘'),
        sa.Column('account_id', sa.String(32), nullable=True, comment='实盘账号ID (live模式)'),
        sa.Column('status', sa.Integer(), server_default='0', comment='部署状态'),
        sa.Column('meta', sa.String(255), server_default='{}'),
        sa.Column('desc', sa.String(255), server_default='This man is lazy, there is no description.'),
        sa.Column('create_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('update_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_del', sa.Boolean(), server_default='0'),
        sa.Column('source', sa.SmallInteger(), server_default='-1'),
        comment='部署记录表',
    )
    op.create_table(
        'user_credentials',
        sa.Column('uuid', sa.String(32), primary_key=True),
        sa.Column('user_id', sa.String(32), sa.ForeignKey('users.uuid'), nullable=False,
                  unique=True, index=True, comment='关联用户UUID（外键 users.uuid）'),
        sa.Column('password_hash', sa.String(256), nullable=False, server_default='', comment='密码哈希'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), comment='凭据是否启用'),
        sa.Column('is_admin', sa.Boolean(), server_default=sa.text('0'), comment='是否管理员'),
        sa.Column('meta', sa.String(255), server_default='{}'),
        sa.Column('desc', sa.String(255), server_default='This man is lazy, there is no description.'),
        sa.Column('create_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('update_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_del', sa.Boolean(), server_default='0'),
        sa.Column('source', sa.SmallInteger(), server_default='-1'),
        comment='用户凭据表',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_credentials')
    op.drop_table('deployment')
