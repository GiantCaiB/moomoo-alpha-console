"""Add metadata columns for signal scoring.

Revision ID: 0040_signal_scoring_metadata
Revises: 0039
Create Date: 2026-07-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0040_signal_scoring_metadata'
down_revision = '87d703529f1e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('signals', sa.Column('failed_filters', sa.JSON(), nullable=True))
    op.add_column('signals', sa.Column('data_quality_status', sa.String(length=50), nullable=True))
    op.add_column('signals', sa.Column('calculated_score_before_filters', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('signals', 'calculated_score_before_filters')
    op.drop_column('signals', 'data_quality_status')
    op.drop_column('signals', 'failed_filters')
