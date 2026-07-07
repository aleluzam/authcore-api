"""empty message

Revision ID: 370a5cb18387
Revises: 70b21c4af1e3
Create Date: 2026-07-07 12:18:24.274007

"""
from typing import Sequence, Union
import uuid
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '370a5cb18387'
down_revision: Union[str, Sequence[str], None] = '70b21c4af1e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Crear la tabla role
    op.create_table(
        'role',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rolename', sa.String(length=15), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Insertar los roles base (ADMIN y USER) con IDs fijos que reutilizamos abajo
    role_table = sa.table(
        'role',
        sa.column('id', sa.UUID()),
        sa.column('rolename', sa.String()),
        sa.column('created_at', sa.DateTime()),
    )
    admin_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.utcnow()

    op.bulk_insert(role_table, [
        {'id': admin_id, 'rolename': 'ADMIN', 'created_at': now},
        {'id': user_id, 'rolename': 'USER', 'created_at': now},
    ])

    # 3. Agregar role_id como nullable (todavía no podemos poner NOT NULL)
    op.add_column('users', sa.Column('role_id', sa.UUID(), nullable=True))
    op.create_foreign_key(None, 'users', 'role', ['role_id'], ['id'])

    # 4. Backfill: mapear el enum viejo 'role' al nuevo role_id
    op.execute(f"""
        UPDATE users
        SET role_id = CASE
            WHEN role = 'ADMIN' THEN '{admin_id}'::uuid
            WHEN role = 'USER' THEN '{user_id}'::uuid
            ELSE '{user_id}'::uuid
        END
    """)

    # 5. Ahora sí, aplicar el constraint NOT NULL
    op.alter_column('users', 'role_id', nullable=False)

    # 6. Borrar la columna vieja (y su tipo enum asociado)
    op.drop_column('users', 'role')
    op.execute("DROP TYPE IF EXISTS roles")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('users', sa.Column('role', postgresql.ENUM('ADMIN', 'USER', name='roles'),
    server_default=sa.text("'USER'::roles"), autoincrement=False, nullable=False))

    op.execute("""
        UPDATE users
        SET role = (
            SELECT CASE WHEN r.rolename = 'ADMIN' THEN 'ADMIN'::roles ELSE 'USER'::roles END
            FROM role r WHERE r.id = users.role_id
        )
    """)

    op.drop_constraint(None, 'users', type_='foreignkey')
    op.drop_column('users', 'role_id')
    op.drop_table('role')
