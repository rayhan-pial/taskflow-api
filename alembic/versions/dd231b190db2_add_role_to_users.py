"""add role to users

Revision ID: dd231b190db2
Revises: f7f690ad5ba2
Create Date: 2026-05-25 16:56:12.366502

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd231b190db2'
down_revision: Union[str, Sequence[str], None] = 'f7f690ad5ba2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role = sa.Enum('admin', 'member', 'viewer', name='user_role')


def upgrade() -> None:
    user_role.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'users',
        sa.Column('role', user_role, nullable=False, server_default='member'),
    )


def downgrade() -> None:
    op.drop_column('users', 'role')
    user_role.drop(op.get_bind(), checkfirst=True)
