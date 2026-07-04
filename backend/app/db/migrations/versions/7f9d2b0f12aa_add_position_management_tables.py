"""add_position_management_tables

Revision ID: 7f9d2b0f12aa
Revises: 0040_signal_scoring_metadata
Create Date: 2026-07-05 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f9d2b0f12aa"
down_revision: Union[str, None] = "0040_signal_scoring_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "position_lifecycle_state",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("original_entry_price", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("original_quantity", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("original_cost_basis", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("highest_price_since_entry", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("trim_25_done", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("trim_50_done", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("trim_75_done", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("tail_mode", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("tail_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tail_original_quantity", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("symbol", name="uq_position_lifecycle_state_symbol"),
    )
    op.create_index("ix_position_lifecycle_state_symbol", "position_lifecycle_state", ["symbol"], unique=False)

    op.create_table(
        "position_management_signals",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("signal", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column("avg_cost", sa.Float(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("gain_pct", sa.Float(), nullable=True),
        sa.Column("suggested_action", sa.Text(), nullable=True),
        sa.Column("suggested_quantity", sa.Integer(), nullable=True),
        sa.Column("suggested_trim_pct", sa.Float(), nullable=True),
        sa.Column("tail_mode", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("weekly_close", sa.Float(), nullable=True),
        sa.Column("weekly_sma20", sa.Float(), nullable=True),
        sa.Column("weekly_sma30", sa.Float(), nullable=True),
        sa.Column("drawdown_from_high", sa.Float(), nullable=True),
        sa.Column("original_cost_basis", sa.Float(), nullable=True),
        sa.Column("highest_price_since_entry", sa.Float(), nullable=True),
        sa.Column("data_source", sa.String(length=50), nullable=True),
        sa.Column("price_source", sa.String(length=50), nullable=True),
        sa.Column("bar_source", sa.String(length=50), nullable=True),
        sa.Column("is_real_market_data", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_position_management_signals_symbol", "position_management_signals", ["symbol"], unique=False)
    op.create_index("ix_position_management_signals_generated_at", "position_management_signals", ["generated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_position_management_signals_generated_at", table_name="position_management_signals")
    op.drop_index("ix_position_management_signals_symbol", table_name="position_management_signals")
    op.drop_table("position_management_signals")

    op.drop_index("ix_position_lifecycle_state_symbol", table_name="position_lifecycle_state")
    op.drop_table("position_lifecycle_state")
