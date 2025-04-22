"""merge multiple heads

Revision ID: 9205a863c464
Revises: 23a8bb636e7e, 7f8a9c3d2e1b
Create Date: 2025-04-22 12:38:13.299681

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9205a863c464'
down_revision = ('23a8bb636e7e', '7f8a9c3d2e1b')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
