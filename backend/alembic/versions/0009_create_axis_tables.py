"""Create AXIS competency, benchmark and match log tables.

Revision ID: 0009_create_axis_tables
Revises: 0008_normalize_profile_subject
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_create_axis_tables"
down_revision: Union[str, None] = "0008_normalize_profile_subject"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "competency_scores",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("s1", sa.Float(), nullable=False, server_default="0"),
        sa.Column("s2", sa.Float(), nullable=False, server_default="0"),
        sa.Column("s3", sa.Float(), nullable=False, server_default="0"),
        sa.Column("s4", sa.Float(), nullable=False, server_default="0"),
        sa.Column("s5", sa.Float(), nullable=False, server_default="0"),
        sa.Column("normalized_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_competency_scores_user_id", "competency_scores", ["user_id"])
    op.create_table(
        "career_benchmarks",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("requirements_json", sa.JSON(), nullable=False),
        sa.Column("ahp_matrix_json", sa.JSON(), nullable=False),
        sa.Column("roc_order_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "match_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("competency_score_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("results_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["competency_score_id"], ["competency_scores.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_match_logs_user_id", "match_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_match_logs_user_id", table_name="match_logs")
    op.drop_table("match_logs")
    op.drop_table("career_benchmarks")
    op.drop_index("ix_competency_scores_user_id", table_name="competency_scores")
    op.drop_table("competency_scores")
