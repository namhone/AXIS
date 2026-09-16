"""Create multi-tenant task and custom tag tables."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_create_tasks"
down_revision: Union[str, None] = "0009_create_axis_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "custom_tags",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tag_name", sa.String(length=80), nullable=False),
        sa.Column("color_hex", sa.String(length=7), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_custom_tags_user_id", "custom_tags", ["user_id"])
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("estimated_time_minutes", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("is_ai_generated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("batch_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_rescheduled_from", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"])
    op.create_index("ix_tasks_scheduled_date", "tasks", ["scheduled_date"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_batch_id", "tasks", ["batch_id"])
    op.create_table(
        "task_tags",
        sa.Column("task_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tag_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["custom_tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "tag_id"),
    )


def downgrade() -> None:
    op.drop_table("task_tags")
    op.drop_index("ix_tasks_batch_id", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_scheduled_date", table_name="tasks")
    op.drop_index("ix_tasks_user_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_custom_tags_user_id", table_name="custom_tags")
    op.drop_table("custom_tags")
