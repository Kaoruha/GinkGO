"""backtest_task metrics columns: String(32) -> Float

Revision ID: a1b2c3d4e5f6
Revises: 84a2de8c7c00
Create Date: 2026-04-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '84a2de8c7c00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change metric columns from String(32) to Float."""
    op.alter_column('backtest_task', 'final_portfolio_value',
                    existing_type=sa.String(32), type_=sa.Float(),
                    existing_server_default='0', server_default='0')
    op.alter_column('backtest_task', 'total_pnl',
                    existing_type=sa.String(32), type_=sa.Float(),
                    existing_server_default='0', server_default='0')
    op.alter_column('backtest_task', 'max_drawdown',
                    existing_type=sa.String(32), type_=sa.Float(),
                    existing_server_default='0', server_default='0')
    op.alter_column('backtest_task', 'sharpe_ratio',
                    existing_type=sa.String(32), type_=sa.Float(),
                    existing_server_default='0', server_default='0')
    op.alter_column('backtest_task', 'annual_return',
                    existing_type=sa.String(32), type_=sa.Float(),
                    existing_server_default='0', server_default='0')
    op.alter_column('backtest_task', 'win_rate',
                    existing_type=sa.String(32), type_=sa.Float(),
                    existing_server_default='0', server_default='0')
    op.alter_column('backtest_task', 'avg_event_processing_ms',
                    existing_type=sa.String(32), type_=sa.Float(),
                    existing_server_default='0', server_default='0')
    op.alter_column('backtest_task', 'peak_memory_mb',
                    existing_type=sa.String(32), type_=sa.Float(),
                    existing_server_default='0', server_default='0')


def downgrade() -> None:
    """Revert metric columns from Float to String(32)."""
    for col in ['avg_event_processing_ms', 'peak_memory_mb',
                'win_rate', 'annual_return', 'sharpe_ratio',
                'max_drawdown', 'total_pnl', 'final_portfolio_value']:
        op.alter_column('backtest_task', col,
                        existing_type=sa.Float(), type_=sa.String(32),
                        existing_server_default='0', server_default='0')
