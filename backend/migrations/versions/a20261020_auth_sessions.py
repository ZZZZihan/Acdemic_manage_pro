"""Add revocable JWT sessions; existing tokens require login again.

Revision ID: a20261020auth
Revises: 24318d21ae1d
"""
from alembic import op
import sqlalchemy as sa

revision = 'a20261020auth'
down_revision = '24318d21ae1d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('auth_sessions',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('revoked_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, nullable=False))
    op.create_index('ix_auth_sessions_user_id', 'auth_sessions', ['user_id'])


def downgrade():
    op.drop_index('ix_auth_sessions_user_id', table_name='auth_sessions')
    op.drop_table('auth_sessions')
