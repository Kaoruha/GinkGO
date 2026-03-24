"""create trade_records table

Revision ID: t088_trade_records
Revises: 0245d8e3a9f1
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 't088_trade_records'
down_revision = '0245d8e3a9f1'
branch_labels = None
depends_on = None


def upgrade():
    """创建交易记录表"""
    op.create_table(
        'trade_records',
        sa.Column('uuid', sa.String(32), primary_key=True),
        sa.Column('live_account_id', sa.String(32), nullable=False, index=True, comment='实盘账号ID'),
        sa.Column('broker_instance_id', sa.String(32), nullable=True, comment='Broker实例ID'),
        sa.Column('portfolio_id', sa.String(32), nullable=True, index=True, comment='Portfolio ID'),
        sa.Column('exchange', sa.String(20), nullable=False, comment='交易所名称'),
        sa.Column('exchange_order_id', sa.String(64), nullable=True, comment='交易所订单ID'),
        sa.Column('exchange_trade_id', sa.String(64), nullable=True, index=True, comment='交易所成交ID'),
        sa.Column('symbol', sa.String(32), nullable=False, index=True, comment='交易标的'),
        sa.Column('side', sa.String(10), nullable=False, comment='交易方向: buy/sell'),
        sa.Column('price', sa.DECIMAL(20, 8), nullable=False, comment='成交价格'),
        sa.Column('quantity', sa.DECIMAL(20, 8), nullable=False, comment='成交数量'),
        sa.Column('quote_quantity', sa.DECIMAL(20, 8), nullable=True, comment='成交金额(计价货币)'),
        sa.Column('fee', sa.DECIMAL(20, 8), nullable=True, comment='手续费'),
        sa.Column('fee_currency', sa.String(20), nullable=True, comment='手续费币种'),
        sa.Column('order_type', sa.String(20), nullable=True, comment='订单类型: market/limit/conditional'),
        sa.Column('time_in_force', sa.String(20), nullable=True, comment='订单有效期: GTC/IOC/FOK'),
        sa.Column('trade_time', sa.DateTime(), nullable=False, index=True, comment='成交时间'),
        sa.Column('trade_timestamp', sa.Integer(), nullable=True, comment='成交时间戳(毫秒)'),
        sa.Column('create_time', sa.DateTime(), nullable=False, comment='记录创建时间'),
        sa.Column('update_time', sa.DateTime(), nullable=True, comment='记录更新时间'),
        sa.Column('strategy_id', sa.String(32), nullable=True, comment='策略ID'),
        sa.Column('signal_id', sa.String(32), nullable=True, comment='信号ID'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注信息'),
        sa.Column('is_del', sa.Integer(), nullable=False, default=False, comment='是否删除'),
        mysql_charset='utf8mb4',
        comment='交易记录表'
    )

    # 创建索引优化查询性能
    op.create_index('idx_trade_records_account_time', 'trade_records', ['live_account_id', 'trade_time'])
    op.create_index('idx_trade_records_portfolio_time', 'trade_records', ['portfolio_id', 'trade_time'])
    op.create_index('idx_trade_records_symbol_time', 'trade_records', ['symbol', 'trade_time'])


def downgrade():
    """删除交易记录表"""
    op.drop_index('idx_trade_records_symbol_time', table_name='trade_records')
    op.drop_index('idx_trade_records_portfolio_time', table_name='trade_records')
    op.drop_index('idx_trade_records_account_time', table_name='trade_records')
    op.drop_table('trade_records')
