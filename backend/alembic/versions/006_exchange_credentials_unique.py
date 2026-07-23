"""enforce one credential set per exchange and user

Revision ID: 006
Revises: 005
"""
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep the newest credential row before enforcing uniqueness. Existing
    # installations could contain duplicates because the API previously used
    # a read-then-insert flow without a database constraint.
    op.execute(
        """
        DELETE FROM exchange_credentials older
        USING exchange_credentials newer
        WHERE older.user_id = newer.user_id
          AND older.exchange = newer.exchange
          AND older.id < newer.id
        """
    )
    op.create_unique_constraint(
        "uq_exchange_credentials_user_exchange",
        "exchange_credentials",
        ["user_id", "exchange"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_exchange_credentials_user_exchange",
        "exchange_credentials",
        type_="unique",
    )
