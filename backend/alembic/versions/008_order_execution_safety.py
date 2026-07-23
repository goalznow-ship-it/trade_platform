"""Add durable order idempotency and exchange tracking."""

from alembic import op
import sqlalchemy as sa


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("exchange", sa.String(20), nullable=False, server_default="binance"))
    op.add_column("orders", sa.Column("client_order_id", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_orders_user_client_order", "orders", ["user_id", "client_order_id"])


def downgrade() -> None:
    op.drop_constraint("uq_orders_user_client_order", "orders", type_="unique")
    op.drop_column("orders", "client_order_id")
    op.drop_column("orders", "exchange")
