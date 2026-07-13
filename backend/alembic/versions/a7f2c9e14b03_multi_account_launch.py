"""Multi-account launch: ad_account_id on FB tables, launch_jobs, campaign_templates

Revision ID: a7f2c9e14b03
Revises: d1a2b3c4d5e6
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'a7f2c9e14b03'
down_revision = 'd1a2b3c4d5e6'
branch_labels = None
depends_on = None

FB_TABLES = ("facebook_campaigns", "facebook_adsets", "facebook_ads")


def upgrade():
    for table in FB_TABLES:
        op.add_column(table, sa.Column('ad_account_id', sa.String(), nullable=True))
        op.create_index(f'ix_{table}_ad_account_id', table, ['ad_account_id'])

    op.create_table(
        'launch_jobs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('status', sa.String(), server_default='pending'),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('total_steps', sa.Integer(), server_default='0'),
        sa.Column('completed_steps', sa.Integer(), server_default='0'),
        sa.Column('failed_steps', sa.Integer(), server_default='0'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_launch_jobs_status', 'launch_jobs', ['status'])

    op.create_table(
        'campaign_templates',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('campaign_templates')
    op.drop_index('ix_launch_jobs_status', table_name='launch_jobs')
    op.drop_table('launch_jobs')
    for table in reversed(FB_TABLES):
        op.drop_index(f'ix_{table}_ad_account_id', table_name=table)
        op.drop_column(table, 'ad_account_id')
