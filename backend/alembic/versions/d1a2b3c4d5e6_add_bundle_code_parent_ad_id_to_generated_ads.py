"""Add bundle_code, parent_ad_id to generated_ads and break_even_roas to brands

Revision ID: d1a2b3c4d5e6
Revises: c122fc0257bd
Create Date: 2026-03-23 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'c122fc0257bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('generated_ads', sa.Column('bundle_code', sa.String(), nullable=True))
    op.add_column('generated_ads', sa.Column('parent_ad_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_generated_ads_bundle_code'), 'generated_ads', ['bundle_code'], unique=False)
    op.create_foreign_key('fk_generated_ads_parent_ad_id', 'generated_ads', 'generated_ads', ['parent_ad_id'], ['id'], ondelete='SET NULL')
    op.add_column('brands', sa.Column('break_even_roas', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('brands', 'break_even_roas')
    op.drop_constraint('fk_generated_ads_parent_ad_id', 'generated_ads', type_='foreignkey')
    op.drop_index(op.f('ix_generated_ads_bundle_code'), table_name='generated_ads')
    op.drop_column('generated_ads', 'parent_ad_id')
    op.drop_column('generated_ads', 'bundle_code')
