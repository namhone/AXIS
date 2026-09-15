"""Backfill and normalize legacy profile subject fields.

Revision ID: 0008_normalize_profile_subject
Revises: 0007_add_profile_exam_subject
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_normalize_profile_subject"
down_revision: Union[str, None] = "0007_add_profile_exam_subject"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    profiles = sa.table(
        "profiles",
        sa.column("user_id", sa.Uuid()),
        sa.column("data", sa.JSON()),
        sa.column("subject", sa.String(length=255)),
    )
    bind = op.get_bind()
    rows = bind.execute(sa.select(profiles.c.user_id, profiles.c.data, profiles.c.subject)).all()
    for user_id, raw_data, stored_subject in rows:
        data = dict(raw_data) if isinstance(raw_data, dict) else {}
        candidates = (stored_subject, data.get("examSubject"), data.get("subject"))
        subject = next(
            (value.strip() for value in candidates if isinstance(value, str) and value.strip()),
            None,
        )
        if subject is None:
            continue
        data["subject"] = subject
        data["examSubject"] = subject
        bind.execute(
            profiles.update()
            .where(profiles.c.user_id == user_id)
            .values(data=data, subject=subject)
        )


def downgrade() -> None:
    profiles = sa.table("profiles", sa.column("subject", sa.String(length=255)))
    op.execute(profiles.update().values(subject=None))
