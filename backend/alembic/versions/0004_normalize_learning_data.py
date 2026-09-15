"""create normalized learning tables

Revision ID: 0004_normalize_learning_data
Revises: 0003_add_account_data
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_normalize_learning_data"
down_revision: Union[str, None] = "0003_add_account_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    common_fk = lambda: sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE")
    op.create_table(
        "goals",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("minutes_per_day", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(32), nullable=False, server_default="general"),
        common_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])
    op.create_table(
        "roadmap_steps",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        common_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roadmap_steps_user_id", "roadmap_steps", ["user_id"])
    op.create_table(
        "assessments",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("score_json", sa.JSON(), nullable=False),
        sa.Column("career_suggestions_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        common_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assessments_user_id", "assessments", ["user_id"])
    # The legacy JSON container is intentionally removed after normalized tables exist.
    op.drop_table("account_data")


def downgrade() -> None:
    op.create_table(
        "account_data",
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.Column("assessment", sa.JSON(), nullable=False),
        sa.Column("development", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    for table in ("assessments", "roadmap_steps", "goals"):
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_table(table)
