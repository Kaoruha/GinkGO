"""Extend portfolio, position, order models for live trading

Revision ID: 0336f9b2c8a2
Revises: 0245d8e3a9f1
Create Date: 2026-03-14 17:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0336f9b2c8a2'
down_revision: Union[str, Sequence[str], None] = '0245d8e3a9f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 扩展 portfolio 表
    op.add_column('portfolio', sa.Column('live_account_id', sa.String(32), nullable=True, comment='关联的实盘账号ID (仅实盘模式)'))
    op.add_column('portfolio', sa.Column('live_status', sa.TINYINT(), nullable=True, comment='实盘连接状态: 0=未连接, 1=已连接, 2=连接中, 3=错误'))
    op.create_index('ix_portfolio_live_account_id', 'portfolio', ['live_account_id'])

    # 扩展 position 表
    op.add_column('position', sa.Column('live_account_id', sa.String(32), nullable=True, comment='实盘账号ID'))
    op.add_column('position', sa.Column('exchange_position_id', sa.String(64), nullable=True, comment='交易所持仓ID'))

    # 扩展 order 表
    op.add_column('order', sa.Column('live_account_id', sa.String(32), nullable=True, comment='实盘账号ID'))
    op.add_column('order', sa.Column('exchange_order_id', sa.String(64), nullable=True, comment='交易所订单ID'))
    op.add_column('order', sa.Column('submit_time', sa.DateTime(timezone=True), nullable=True, comment='提交到交易所的时间'))
    op.add_column('order', sa.Column('exchange_response', sa.Text(), nullable=True, comment='交易所响应信息'))


def downgrade() -> None:
    """Downgrade schema."""

    # 回退 order 表扩展
    op.drop_column('order', 'exchange_response')
    op.drop_column('order', 'submit_time')
    op.drop_column('order', 'exchange_order_id')
    op.drop_column('order', 'live_account_id')

    # 回退 position 表扩展
    op.drop_column('position', 'exchange_position_id')
    op.drop_column('position', 'live_account_id')

    # 回退 portfolio 表扩展
    op.drop_index('ix_portfolio_live_account_id', table_name='portfolio')
    op.drop_column('portfolio', 'live_status')
    op.drop_column('portfolio', 'live_account_id')
