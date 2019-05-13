"""add extended data about tower

Revision ID: b9df7cd058d7
Revises: 6d0126ce7607
Create Date: 2019-05-08 11:24:38.288809

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'b9df7cd058d7'
down_revision = '6d0126ce7607'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tower_data', sa.Column('cfo', sa.Float(), nullable=True))
    op.add_column('tower_data', sa.Column('raw_sib1', sa.String(255), nullable=True))
    op.add_column('tower_data', sa.Column('rssi', sa.Float(), nullable=True))
    op.drop_column('tower_data', 'rsrp')


def downgrade():
    op.add_column('tower_data', sa.Column('rsrp', mysql.FLOAT(), nullable=True))
    op.drop_column('tower_data', 'rssi')
    op.drop_column('tower_data', 'raw_sib1')
    op.drop_column('tower_data', 'cfo')
