"""Add academic monitoring tables (Student, Subject)

Revision ID: 004_add_academic_tables
Revises: 003_create_admin_user
Create Date: 2026-03-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_add_academic_tables"
down_revision: Union[str, None] = "003_create_admin_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "academic_students",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("course", sa.String(), nullable=False),
        sa.Column("semester", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_academic_students_student_id"),
        "academic_students",
        ["student_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_academic_students_email"),
        "academic_students",
        ["email"],
        unique=False,
    )

    op.create_table(
        "academic_subjects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("subject_name", sa.String(), nullable=False),
        sa.Column("attendance", sa.Float(), nullable=True),
        sa.Column("cia_scores", sa.JSON(), nullable=True),
        sa.Column("mid_sem", sa.Float(), nullable=True),
        sa.Column("end_sem", sa.Float(), nullable=True),
        sa.Column("practical", sa.Float(), nullable=True),
        sa.Column("remarks", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["academic_students.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("academic_subjects")
    op.drop_index(
        op.f("ix_academic_students_email"),
        table_name="academic_students",
    )
    op.drop_index(
        op.f("ix_academic_students_student_id"),
        table_name="academic_students",
    )
    op.drop_table("academic_students")
