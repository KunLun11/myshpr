"""admin audit log

Revision ID: 0002_audit_log
Revises: 7262fd259de0
Create Date: 2026-11-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_audit_log"
down_revision: Union[str, None] = "7262fd259de0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("school_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_audit_log_actor_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
            name=op.f("fk_audit_log_school_id_schools"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(
        "ix_audit_log_school_created",
        "audit_log",
        ["school_id", "created_at"],
    )
    op.create_index(
        "ix_audit_log_action_created",
        "audit_log",
        ["action", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_action_created", table_name="audit_log")
    op.drop_index("ix_audit_log_school_created", table_name="audit_log")
    op.drop_table("audit_log")
