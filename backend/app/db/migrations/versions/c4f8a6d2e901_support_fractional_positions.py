"""support fractional share quantities in holdings and guidance

Revision ID: c4f8a6d2e901
Revises: 7f9d2b0f12aa
Create Date: 2026-07-15 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4f8a6d2e901"
down_revision: Union[str, Sequence[str], None] = ("7f9d2b0f12aa", "2e9f8a1b3c5d")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("positions") as batch_op:
        batch_op.alter_column("quantity", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table("position_lifecycle_state") as batch_op:
        batch_op.alter_column("original_quantity", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column("tail_original_quantity", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=True)

    with op.batch_alter_table("position_management_signals") as batch_op:
        batch_op.alter_column("quantity", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column("suggested_quantity", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("position_management_signals") as batch_op:
        batch_op.alter_column("suggested_quantity", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=True)
        batch_op.alter_column("quantity", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=True)

    with op.batch_alter_table("position_lifecycle_state") as batch_op:
        batch_op.alter_column("tail_original_quantity", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=True)
        batch_op.alter_column("original_quantity", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=False)

    with op.batch_alter_table("positions") as batch_op:
        batch_op.alter_column("quantity", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=False)
