"""Create broker_instances table for live trading

Revision ID: 0245d8e3a9f1
Revises: 0162c5cd727c
Create Date: 2026-03-14 17:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0245d8e3a9f1'
down_revision: Union[str, Sequence[str], None] = '0162c5cd727c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'broker_instances',
        sa.Column('uuid', sa.String(32), primary_key=True),
        sa.Column('portfolio_id', sa.String(32), nullable=False, unique=True, index=True, comment='关联的Portfolio ID'),
        sa.Column('live_account_id', sa.String(32), nullable=False, index=True, comment='关联的实盘账号ID'),

        # 状态字段
        sa.Column('state', sa.String(20), nullable=False, server_default='uninitialized', comment='Broker状态'),
        sa.Column('process_id', sa.Integer(), comment='Broker进程ID'),
        sa.Column('heartbeat_at', sa.DateTime(timezone=True), comment='最后心跳时间'),

        # 错误处理
        sa.Column('error_message', sa.Text(), comment='错误消息'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0', comment='累计错误次数'),

        # 订单统计
        sa.Column('total_submitted', sa.Integer(), nullable=False, server_default='0', comment='累计提交订单数'),
        sa.Column('total_filled', sa.Integer(), nullable=False, server_default='0', comment='累计成交订单数'),
        sa.Column('total_cancelled', sa.Integer(), nullable=False, server_default='0', comment='累计撤销订单数'),
        sa.Column('total_rejected', sa.Integer(), nullable=False, server_default='0', comment='累计拒绝订单数'),
        sa.Column('last_order_at', sa.DateTime(timezone=True), comment='最后订单时间'),

        # 标准字段
        sa.Column('meta', sa.String(255), server_default='{}', comment='元数据JSON'),
        sa.Column('desc', sa.String(255), server_default='Broker instance for live trading', comment='描述'),
        sa.Column('create_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('update_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='更新时间'),
        sa.Column('is_del', sa.Boolean(), server_default='0', comment='软删除标记'),
        sa.Column('source', sa.String(10), server_default='-1', comment='数据来源'),

        sa.ForeignKeyConstraint(['live_account_id'], ['live_accounts.uuid'], name='fk_broker_live_account'),
        comment='Broker实例表 - 跟踪Portfolio的Broker运行状态'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('broker_instances')
