"""Add the selected exam subject to account profiles.

Revision ID: 0007_add_profile_exam_subject
Revises: 0006_add_user_full_name
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_add_profile_exam_subject"
down_revision: Union[str, None] = "0006_add_user_full_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("profiles")}
    if "subject" not in columns:
        op.add_column("profiles", sa.Column("subject", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "subject")
