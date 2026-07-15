"""Add dedicated Entry Signal and Position Guidance run history."""

from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "c4f8a6d2e901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entry_signal_runs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("strategy_profile_id", sa.String(36), nullable=True),
        sa.Column("strategy_name", sa.String(100), nullable=False),
        sa.Column("strategy_version", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="RUNNING"),
        sa.Column("symbols_scanned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("signals_generated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data_error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("parameters_snapshot_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["strategy_profile_id"], ["strategy_profiles.id"]),
    )
    op.create_table(
        "position_guidance_runs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("strategy_profile_id", sa.String(36), nullable=True),
        sa.Column("strategy_name", sa.String(100), nullable=False),
        sa.Column("strategy_version", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="RUNNING"),
        sa.Column("positions_scanned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("signals_generated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data_error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("parameters_snapshot_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["strategy_profile_id"], ["strategy_profiles.id"]),
    )
    op.add_column("signals", sa.Column("run_id", sa.String(36), nullable=True))
    op.add_column("position_management_signals", sa.Column("run_id", sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column("position_management_signals", "run_id")
    op.drop_column("signals", "run_id")
    op.drop_table("position_guidance_runs")
    op.drop_table("entry_signal_runs")
