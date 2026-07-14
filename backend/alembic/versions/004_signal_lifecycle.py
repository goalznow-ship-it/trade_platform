"""Add signal lifecycle tracking (result field)

Revision ID: 004
Revises: 003
Create Date: 2026-07-14
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("signals", sa.Column("result", sa.String(20), nullable=True))
    op.create_index("ix_signals_result", "signals", ["result"])
    op.create_index("ix_signals_direction_result", "signals", ["direction", "result"])


def downgrade() -> None:
    op.drop_index("ix_signals_direction_result", table_name="signals")
    op.drop_index("ix_signals_result", table_name="signals")
    op.drop_column("signals", "result")
