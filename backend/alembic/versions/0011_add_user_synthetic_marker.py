"""Add a persistent synthetic-data provenance marker to users."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_add_user_synthetic_marker"
down_revision: Union[str, None] = "0010_create_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_synthetic",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_synthetic")
