"""empty message

Revision ID: 70b21c4af1e3
Revises: adde16fcf394
Create Date: 2026-04-06 22:37:38.119703

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70b21c4af1e3'
down_revision: Union[str, Sequence[str], None] = 'adde16fcf394'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    roles_enum = sa.Enum('ADMIN', 'USER', name='roles')
    roles_enum.create(op.get_bind())
    op.add_column('users', sa.Column(
        'role',
        roles_enum,
        nullable=False,
        server_default='USER'  # valor para registros existentes
    ))

def downgrade() -> None:
    op.drop_column('users', 'role')
    sa.Enum(name='roles').drop(op.get_bind())