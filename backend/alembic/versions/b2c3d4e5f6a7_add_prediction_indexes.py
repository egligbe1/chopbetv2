"""Add status + composite indexes on predictions for stats/results queries

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(conn, index_name: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :idx"),
        {"idx": index_name}
    )
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # Single-column index on status (filtered by results checker + stats).
    if not _index_exists(conn, 'ix_predictions_status'):
        op.create_index(op.f('ix_predictions_status'), 'predictions', ['status'], unique=False)

    # Composite (sport, status): every stats endpoint filters on both.
    if not _index_exists(conn, 'ix_predictions_sport_status'):
        op.create_index('ix_predictions_sport_status', 'predictions', ['sport', 'status'], unique=False)

    # Composite (sport, date): the today/date/history windows filter on both.
    if not _index_exists(conn, 'ix_predictions_sport_date'):
        op.create_index('ix_predictions_sport_date', 'predictions', ['sport', 'date'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_predictions_sport_date', table_name='predictions')
    op.drop_index('ix_predictions_sport_status', table_name='predictions')
    op.drop_index(op.f('ix_predictions_status'), table_name='predictions')
