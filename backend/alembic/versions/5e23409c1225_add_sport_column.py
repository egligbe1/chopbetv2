"""Add sport column

Revision ID: 5e23409c1225
Revises: 
Create Date: 2026-03-01 21:42:03.710238

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e23409c1225'
down_revision: Union[str, None] = None
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


def _index_exists(conn, index_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname = :idx"
        ),
        {"idx": index_name}
    )
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, 'accuracy_stats', 'sport'):
        op.add_column('accuracy_stats', sa.Column('sport', sa.String(), nullable=True))

    if not _column_exists(conn, 'predictions', 'sport'):
        op.add_column('predictions', sa.Column('sport', sa.String(), nullable=True))

    if not _index_exists(conn, 'ix_accuracy_stats_sport'):
        op.create_index(op.f('ix_accuracy_stats_sport'), 'accuracy_stats', ['sport'], unique=False)

    if not _index_exists(conn, 'ix_predictions_sport'):
        op.create_index(op.f('ix_predictions_sport'), 'predictions', ['sport'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_predictions_sport'), table_name='predictions')
    op.drop_column('predictions', 'sport')
    op.drop_index(op.f('ix_accuracy_stats_sport'), table_name='accuracy_stats')
    op.drop_column('accuracy_stats', 'sport')
