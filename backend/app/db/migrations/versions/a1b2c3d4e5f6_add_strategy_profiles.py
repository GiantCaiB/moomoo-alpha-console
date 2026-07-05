"""add_strategy_profiles

Revision ID: a1b2c3d4e5f6
Revises: 7f9d2b0f12aa
Create Date: 2026-07-05 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "7f9d2b0f12aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "strategy_profiles",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("strategy_type", sa.String(length=30), nullable=False),
        sa.Column("strategy_key", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parameters_json", sa.Text(), nullable=True),
        sa.Column("rules_summary_json", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_strategy_profiles_type", "strategy_profiles", ["strategy_type"], unique=False)

    op.add_column("signals", sa.Column("strategy_profile_id", sa.CHAR(36), sa.ForeignKey("strategy_profiles.id"), nullable=True))
    op.add_column("signals", sa.Column("strategy_version", sa.String(length=20), nullable=True))
    op.add_column("signals", sa.Column("parameters_snapshot_json", sa.Text(), nullable=True))

    op.add_column("position_management_signals", sa.Column("strategy_profile_id", sa.CHAR(36), sa.ForeignKey("strategy_profiles.id"), nullable=True))
    op.add_column("position_management_signals", sa.Column("strategy_version", sa.String(length=20), nullable=True))
    op.add_column("position_management_signals", sa.Column("parameters_snapshot_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("position_management_signals", "parameters_snapshot_json")
    op.drop_column("position_management_signals", "strategy_version")
    op.drop_column("position_management_signals", "strategy_profile_id")

    op.drop_column("signals", "parameters_snapshot_json")
    op.drop_column("signals", "strategy_version")
    op.drop_column("signals", "strategy_profile_id")

    op.drop_index("ix_strategy_profiles_type", table_name="strategy_profiles")
    op.drop_table("strategy_profiles")
