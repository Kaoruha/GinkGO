"""Create live_accounts table for OKX trading

Revision ID: 0162c5cd727c
Revises: 
Create Date: 2026-03-14 01:27:51.414314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0162c5cd727c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'live_accounts',
        sa.Column('uuid', sa.String(32), primary_key=True),
        sa.Column('user_id', sa.String(32), nullable=False, index=True, comment='所属用户ID'),
        sa.Column('exchange', sa.String(20), nullable=False, comment='交易所类型 (okx/binance)'),
        sa.Column('environment', sa.String(20), nullable=False, server_default='testnet', comment='环境 (production/testnet)'),
        sa.Column('name', sa.String(100), nullable=False, comment='账号名称'),
        sa.Column('description', sa.Text(), comment='账号描述'),
        sa.Column('api_key', sa.String(500), nullable=False, comment='加密的API Key'),
        sa.Column('api_secret', sa.String(500), nullable=False, comment='加密的API Secret'),
        sa.Column('passphrase', sa.String(500), comment='加密的Passphrase (OKX需要)'),
        sa.Column('status', sa.String(20), nullable=False, server_default='enabled', comment='账号状态'),
        sa.Column('last_validated_at', sa.DateTime(timezone=True), comment='上次验证时间'),
        sa.Column('validation_status', sa.String(100), comment='验证状态消息'),
        sa.Column('meta', sa.String(255), server_default='{}', comment='元数据JSON'),
        sa.Column('desc', sa.String(255), server_default='Live trading account', comment='描述'),
        sa.Column('create_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('update_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='更新时间'),
        sa.Column('is_del', sa.Boolean(), server_default='0', comment='软删除标记'),
        sa.Column('source', sa.String(10), server_default='-1', comment='数据来源'),
        comment='实盘账号表 - 存储加密的API凭证'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('live_accounts')
