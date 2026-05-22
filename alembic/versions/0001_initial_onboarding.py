"""initial onboarding schema

Revision ID: 0001_initial_onboarding
Revises: 
Create Date: 2026-05-22 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial_onboarding"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("last_name", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False, unique=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
    )
    op.create_index("ix_candidate_modified", "candidate", ["last_modified_at", "version"])

    op.create_table(
        "onboarding_process",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("candidate_id", sa.String(length=64), sa.ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False),
        sa.Column("current_stage", sa.String(length=64), nullable=False),
        sa.Column("doj", sa.Date(), nullable=True),
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
    )
    op.create_index("ix_process_modified", "onboarding_process", ["last_modified_at", "version"])

    op.create_table(
        "onboarding_task",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("process_id", sa.String(length=64), sa.ForeignKey("onboarding_process.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("assignee_type", sa.String(length=32), nullable=False),
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
    )
    op.create_index("ix_task_modified", "onboarding_task", ["last_modified_at", "version"])

    op.create_table(
        "onboarding_activity",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("process_id", sa.String(length=64), sa.ForeignKey("onboarding_process.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
    )
    op.create_index("ix_activity_modified", "onboarding_activity", ["last_modified_at", "version"])

    op.create_table(
        "document",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("candidate_id", sa.String(length=64), sa.ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
    )
    op.create_index("ix_document_modified", "document", ["last_modified_at", "version"])

    op.create_table(
        "event_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_name", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("event_log")
    op.drop_index("ix_document_modified", table_name="document")
    op.drop_table("document")
    op.drop_index("ix_activity_modified", table_name="onboarding_activity")
    op.drop_table("onboarding_activity")
    op.drop_index("ix_task_modified", table_name="onboarding_task")
    op.drop_table("onboarding_task")
    op.drop_index("ix_process_modified", table_name="onboarding_process")
    op.drop_table("onboarding_process")
    op.drop_index("ix_candidate_modified", table_name="candidate")
    op.drop_table("candidate")
