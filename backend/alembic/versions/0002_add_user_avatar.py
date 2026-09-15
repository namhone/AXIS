"""add avatar fields to users

Revision ID: 0002_add_user_avatar
Revises: 0001_create_users
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_add_user_avatar"
down_revision: Union[str, None] = "0001_create_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_data", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("avatar_mime_type", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_mime_type")
    op.drop_column("users", "avatar_data")
