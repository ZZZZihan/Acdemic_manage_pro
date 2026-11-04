"""add access_scope to tech_summaries

Revision ID: b7e2c1d94a10
Revises: 24318d21ae1d
Create Date: 2026-11-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b7e2c1d94a10"
down_revision = "24318d21ae1d"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tech_summaries" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("tech_summaries")}
    if "access_scope" in columns:
        return
    op.add_column(
        "tech_summaries",
        sa.Column("access_scope", sa.String(length=32), nullable=True, server_default="lab"),
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tech_summaries" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("tech_summaries")}
    if "access_scope" not in columns:
        return
    op.drop_column("tech_summaries", "access_scope")
