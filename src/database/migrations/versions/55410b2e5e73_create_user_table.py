"""Create user table

Revision ID: 55410b2e5e73
Revises: 
Create Date: 2024-04-04 19:02:57.661466

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = '55410b2e5e73'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("username", sa.String, unique=True, index=True),
        sa.Column("email", sa.String, unique=True, index=True),
        sa.Column("password_hash", sa.String),
        sa.Column("salt", sa.String(4), nullable=False, server_default='QWDS')
    )

def downgrade():
    op.drop_table("users")
