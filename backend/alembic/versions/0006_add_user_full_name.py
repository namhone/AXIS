"""Add the name captured during registration to users.

Revision ID: 0006_add_user_full_name
Revises: 0005_add_profiles
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_add_user_full_name"
down_revision: Union[str, None] = "0005_add_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "full_name" not in columns:
        op.add_column(
            "users",
            sa.Column("full_name", sa.String(length=120), nullable=False, server_default=""),
        )


def downgrade() -> None:
    op.drop_column("users", "full_name")
