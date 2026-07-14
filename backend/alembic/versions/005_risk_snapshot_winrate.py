"""Add win_rate column to risk_snapshots

Revision ID: 005
Revises: 004
Create Date: 2026-07-14
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("risk_snapshots", sa.Column("win_rate", sa.Float(), nullable=True, server_default="0.0"))


def downgrade() -> None:
    op.drop_column("risk_snapshots", "win_rate")
