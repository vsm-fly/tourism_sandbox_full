"""add bank_account_id to bank_operations

Revision ID: e1930e510ae0
Revises: bf3f97073f7e
Create Date: 2025-09-29 03:27:57.503044

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1930e510ae0'
down_revision = 'bf3f97073f7e'
branch_labels = None
depends_on = None


def upgrade():
    # 1) Добавляем колонку (пока nullable) + индекс
    op.add_column('bank_operations', sa.Column('bank_account_id', sa.Integer(), nullable=True))
    op.create_index('ix_bank_operations_bank_account_id', 'bank_operations', ['bank_account_id'])

    # 2) Бэкфилл по номеру счёта (MySQL/MariaDB синтаксис)
    op.execute("""
        UPDATE bank_operations bo
        JOIN bank_accounts ba ON ba.number = bo.account_number
        SET bo.bank_account_id = ba.id
    """)

    # 3) Внешний ключ
    op.create_foreign_key(
        'fk_bank_operations_account',
        'bank_operations', 'bank_accounts',
        ['bank_account_id'], ['id'],
        onupdate='CASCADE', ondelete='RESTRICT'
    )

    # 4) (опционально, отдельной ревизией) — сделать NOT NULL,
    # когда убедимся, что нет строк с NULL:
    # op.alter_column('bank_operations', 'bank_account_id',
    #                 existing_type=sa.Integer(), nullable=False)


def downgrade():
    # Откатываем: сначала FK, затем индекс и колонку
    op.drop_constraint('fk_bank_operations_account', 'bank_operations', type_='foreignkey')
    op.drop_index('ix_bank_operations_bank_account_id', table_name='bank_operations')
    op.drop_column('bank_operations', 'bank_account_id')
