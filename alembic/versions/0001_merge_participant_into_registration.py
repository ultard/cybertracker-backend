"""Merge participant into registration (user_id) and drop participants.

Revision ID: 0001_merge_participant_into_registration
Revises:
Create Date: 2026-04-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_merge_participant_into_registration"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # registrations.user_id (new)
    with op.batch_alter_table("registrations") as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch.create_index("ix_registrations_user_id", ["user_id"])

    # Copy registrations.participant_id -> registrations.user_id via participants.user_id
    op.execute(
        sa.text(
            """
            UPDATE registrations r
            SET user_id = p.user_id
            FROM participants p
            WHERE r.participant_id = p.id
            """
        )
    )

    # Drop registrations that can't be mapped to a user (participant.user_id was NULL)
    op.execute(sa.text("DELETE FROM registrations WHERE user_id IS NULL"))

    # attendance_logs.participant_id (drop)
    with op.batch_alter_table("attendance_logs") as batch:
        batch.drop_column("participant_id")

    # registrations.participant_id (drop + constraint swap)
    with op.batch_alter_table("registrations") as batch:
        batch.drop_constraint("uq_reg_participant_tournament", type_="unique")
        batch.drop_column("participant_id")
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch.create_unique_constraint("uq_reg_user_tournament", ["user_id", "tournament_id"])

    # participants (drop)
    op.drop_table("participants")


def downgrade() -> None:
    # Recreate participants table (best-effort) and restore columns.
    op.create_table(
        "participants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_participants_user_id"),
    )

    with op.batch_alter_table("registrations") as batch:
        batch.add_column(sa.Column("participant_id", sa.Integer(), nullable=True))
        batch.create_index("ix_registrations_participant_id", ["participant_id"])

    # Backfill participants from registrations.user_id
    op.execute(
        sa.text(
            """
            INSERT INTO participants (user_id, status)
            SELECT DISTINCT r.user_id, 'active'
            FROM registrations r
            WHERE r.user_id IS NOT NULL
            ON CONFLICT (user_id) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE registrations r
            SET participant_id = p.id
            FROM participants p
            WHERE r.user_id = p.user_id
            """
        )
    )

    with op.batch_alter_table("registrations") as batch:
        batch.drop_constraint("uq_reg_user_tournament", type_="unique")
        batch.drop_index("ix_registrations_user_id")
        batch.drop_column("user_id")
        batch.alter_column("participant_id", existing_type=sa.Integer(), nullable=False)
        batch.create_unique_constraint(
            "uq_reg_participant_tournament", ["participant_id", "tournament_id"]
        )

    with op.batch_alter_table("attendance_logs") as batch:
        batch.add_column(sa.Column("participant_id", sa.Integer(), nullable=False))
