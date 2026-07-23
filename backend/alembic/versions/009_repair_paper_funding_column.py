"""Repair legacy paper funding timestamp column naming."""

from alembic import op
import sqlalchemy as sa


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("paper_positions")
    }
    if "last_funding_at" not in columns:
        if "last_funding_time" in columns:
            op.alter_column(
                "paper_positions",
                "last_funding_time",
                new_column_name="last_funding_at",
            )
        else:
            op.add_column(
                "paper_positions",
                sa.Column("last_funding_at", sa.DateTime(timezone=True), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("paper_positions")
    }
    if "last_funding_at" in columns and "last_funding_time" not in columns:
        op.alter_column(
            "paper_positions",
            "last_funding_at",
            new_column_name="last_funding_time",
        )
