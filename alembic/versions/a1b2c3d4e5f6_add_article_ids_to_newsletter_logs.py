"""add article_ids to newsletter_logs

Revision ID: a1b2c3d4e5f6
Revises: e7d2de3acad1
Create Date: 2026-05-26 08:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "e7d2de3acad1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "newsletter_logs",
        sa.Column("article_ids", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("newsletter_logs", "article_ids")
