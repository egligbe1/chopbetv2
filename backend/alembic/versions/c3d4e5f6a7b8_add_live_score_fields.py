"""Add live score snapshot fields to predictions

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :col"
        ),
        {"table": table_name, "col": column_name}
    )
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()
    if not _column_exists(conn, 'predictions', 'live_home'):
        op.add_column('predictions', sa.Column('live_home', sa.Integer(), nullable=True))
    if not _column_exists(conn, 'predictions', 'live_away'):
        op.add_column('predictions', sa.Column('live_away', sa.Integer(), nullable=True))
    if not _column_exists(conn, 'predictions', 'live_status'):
        op.add_column('predictions', sa.Column('live_status', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('predictions', 'live_status')
    op.drop_column('predictions', 'live_away')
    op.drop_column('predictions', 'live_home')
