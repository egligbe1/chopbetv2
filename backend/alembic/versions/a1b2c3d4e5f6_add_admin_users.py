"""Add admin_users table

Revision ID: a1b2c3d4e5f6
Revises: 5e23409c1225
Create Date: 2026-07-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5e23409c1225'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :table"
        ),
        {"table": table_name}
    )
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _table_exists(conn, 'admin_users'):
        op.create_table(
            'admin_users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('username', sa.String(), nullable=False),
            sa.Column('password_hash', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_admin_users_id'), 'admin_users', ['id'], unique=False)
        op.create_index(op.f('ix_admin_users_username'), 'admin_users', ['username'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_admin_users_username'), table_name='admin_users')
    op.drop_index(op.f('ix_admin_users_id'), table_name='admin_users')
    op.drop_table('admin_users')
