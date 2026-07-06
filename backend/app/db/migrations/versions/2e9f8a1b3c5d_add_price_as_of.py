"""add_price_as_of_to_signals

Revision ID: 2e9f8a1b3c5d
Revises: a1b2c3d4e5f6
Create Date: 2026-07-07 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "2e9f8a1b3c5d"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("signals", sa.Column("price_as_of", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("signals", "price_as_of")
