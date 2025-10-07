"""bank_account_id not null

Revision ID: e05873125e1d
Revises: e1930e510ae0
Create Date: 2025-09-29 03:36:24.500506

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e05873125e1d'
down_revision = 'e1930e510ae0'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'bank_operations',
        'bank_account_id',
        existing_type=sa.Integer(),
        nullable=False
    )


def downgrade():
    op.alter_column(
        'bank_operations',
        'bank_account_id',
        existing_type=sa.Integer(),
        nullable=True
    )
