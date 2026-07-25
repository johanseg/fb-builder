"""durable launch worker and Meta reporting foundation

Revision ID: c8d4e1f2a901
Revises: a7f2c9e14b03
"""
from alembic import op
import sqlalchemy as sa


revision = "c8d4e1f2a901"
down_revision = "a7f2c9e14b03"
branch_labels = None
depends_on = None


def upgrade():
    # Existing role seeding does not know about explicit activation approval.
    op.execute("""
        INSERT INTO permissions (id, name, description)
        SELECT md5('campaigns:activate'), 'campaigns:activate', 'Activate verified Meta launches'
        WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE name = 'campaigns:activate')
    """)
    op.execute("""
        INSERT INTO permissions (id, name, description) VALUES
            (md5('reporting:read'), 'reporting:read', 'View Meta reporting'),
            (md5('reporting:write'), 'reporting:write', 'Manage reporting settings'),
            (md5('reporting:sync'), 'reporting:sync', 'Run Meta reporting syncs')
        ON CONFLICT (name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT roles.id, permissions.id FROM roles JOIN permissions ON permissions.name = 'campaigns:activate'
        WHERE roles.name IN ('admin', 'manager')
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT roles.id, permissions.id
        FROM roles JOIN permissions ON (
            (roles.name IN ('viewer', 'editor', 'manager', 'admin') AND permissions.name = 'reporting:read')
            OR (roles.name IN ('manager', 'admin') AND permissions.name IN ('reporting:write', 'reporting:sync'))
        )
        ON CONFLICT DO NOTHING
    """)
    op.add_column("brands", sa.Column("lookback_days", sa.Integer(), nullable=True))
    op.alter_column(
        "brands",
        "break_even_roas",
        existing_type=sa.Float(),
        type_=sa.Numeric(18, 6),
        postgresql_using="break_even_roas::numeric",
        existing_nullable=True,
    )
    op.add_column("brands", sa.Column("min_spend", sa.Numeric(18, 2), nullable=True))
    op.add_column("brands", sa.Column("scale_roas", sa.Numeric(18, 6), nullable=True))
    op.add_column("brands", sa.Column("min_purchases", sa.Integer(), nullable=True))

    op.create_table(
        "brand_ad_accounts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("brand_id", sa.String(), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meta_account_id", sa.String(), nullable=False, unique=True),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("timezone", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_brand_ad_accounts_brand_id", "brand_ad_accounts", ["brand_id"])

    op.create_table(
        "meta_sync_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("brand_ad_account_id", sa.String(), sa.ForeignKey("brand_ad_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.String(), nullable=True),
        sa.Column("lookback_days", sa.Integer(), nullable=True),
        sa.Column("cursor", sa.String(), nullable=True),
        sa.Column("totals", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_meta_sync_runs_account", "meta_sync_runs", ["brand_ad_account_id"])

    op.create_table(
        "meta_insight_daily",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("brand_ad_account_id", sa.String(), sa.ForeignKey("brand_ad_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meta_sync_run_id", sa.String(), sa.ForeignKey("meta_sync_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("meta_ad_id", sa.String(), nullable=False),
        sa.Column("date_start", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("spend", sa.Numeric(18, 2), nullable=True),
        sa.Column("impressions", sa.Integer(), nullable=True),
        sa.Column("clicks", sa.Integer(), nullable=True),
        sa.Column("actions", sa.JSON(), nullable=True),
        sa.Column("purchase_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("meta_campaign_id", sa.String(), nullable=True),
        sa.Column("meta_adset_id", sa.String(), nullable=True),
        sa.Column("campaign_name", sa.String(), nullable=True),
        sa.Column("adset_name", sa.String(), nullable=True),
        sa.Column("ad_name", sa.String(), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("brand_ad_account_id", "meta_ad_id", "date_start", name="uq_meta_insight_daily_ad_date"),
    )
    op.create_index("ix_meta_insight_daily_account", "meta_insight_daily", ["brand_ad_account_id"])
    op.create_index("ix_meta_insight_daily_sync", "meta_insight_daily", ["meta_sync_run_id"])

    op.create_table(
        "facebook_ad_modules",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("facebook_ad_id", sa.String(), sa.ForeignKey("facebook_ads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ad_module_id", sa.String(), sa.ForeignKey("ad_modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("facebook_ad_id", "ad_module_id", name="uq_facebook_ad_modules_ad_module"),
    )
    op.create_index("ix_facebook_ad_modules_ad", "facebook_ad_modules", ["facebook_ad_id"])
    op.create_index("ix_facebook_ad_modules_module", "facebook_ad_modules", ["ad_module_id"])

    op.add_column("launch_jobs", sa.Column("idempotency_key", sa.String(), nullable=True))
    op.add_column("launch_jobs", sa.Column("payload_sha256", sa.String(length=64), nullable=True))
    op.add_column("launch_jobs", sa.Column("activation_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("launch_jobs", sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_launch_jobs_creator_idempotency", "launch_jobs", ["created_by", "idempotency_key"])

    op.create_table(
        "launch_targets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), sa.ForeignKey("launch_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ad_account_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("campaign_fb_id", sa.String(), nullable=True),
        sa.Column("adset_fb_id", sa.String(), nullable=True),
        sa.Column("campaign_owned_by_launch", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("adset_owned_by_launch", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("job_id", "ad_account_id", name="uq_launch_targets_job_account"),
        sa.CheckConstraint("status IN ('queued','building','reconciliation_required','ready','activating','active','failed')", name="ck_launch_targets_status"),
    )
    op.create_index("ix_launch_targets_job", "launch_targets", ["job_id"])
    op.create_index("ix_launch_targets_status", "launch_targets", ["status"])

    op.create_table(
        "launch_operations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("target_id", sa.String(), sa.ForeignKey("launch_targets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("operation_key", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("fb_object_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("target_id", "operation_key", name="uq_launch_operations_target_key"),
        sa.CheckConstraint("status IN ('pending','leased','succeeded','retryable','needs_reconciliation','failed','cancelled')", name="ck_launch_operations_status"),
    )
    op.create_index("ix_launch_operations_target", "launch_operations", ["target_id"])
    op.create_index("ix_launch_operations_status", "launch_operations", ["status"])
    op.create_index("ix_launch_operations_available", "launch_operations", ["available_at"])
    op.create_index("ix_launch_operations_lease", "launch_operations", ["lease_expires_at"])


def downgrade():
    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE name LIKE 'reporting:%')")
    op.execute("DELETE FROM permissions WHERE name LIKE 'reporting:%'")
    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE name = 'campaigns:activate')")
    op.execute("DELETE FROM permissions WHERE name = 'campaigns:activate'")
    for name, table in (("ix_launch_operations_lease", "launch_operations"), ("ix_launch_operations_available", "launch_operations"), ("ix_launch_operations_status", "launch_operations"), ("ix_launch_operations_target", "launch_operations")):
        op.drop_index(name, table_name=table)
    op.drop_table("launch_operations")
    for name, table in (("ix_launch_targets_status", "launch_targets"), ("ix_launch_targets_job", "launch_targets")):
        op.drop_index(name, table_name=table)
    op.drop_table("launch_targets")
    op.drop_constraint("uq_launch_jobs_creator_idempotency", "launch_jobs", type_="unique")
    for column in ("activated_at", "activation_requested_at", "payload_sha256", "idempotency_key"):
        op.drop_column("launch_jobs", column)
    op.drop_index("ix_facebook_ad_modules_module", table_name="facebook_ad_modules")
    op.drop_index("ix_facebook_ad_modules_ad", table_name="facebook_ad_modules")
    op.drop_table("facebook_ad_modules")
    op.drop_index("ix_meta_insight_daily_sync", table_name="meta_insight_daily")
    op.drop_index("ix_meta_insight_daily_account", table_name="meta_insight_daily")
    op.drop_table("meta_insight_daily")
    op.drop_index("ix_meta_sync_runs_account", table_name="meta_sync_runs")
    op.drop_table("meta_sync_runs")
    op.drop_index("ix_brand_ad_accounts_brand_id", table_name="brand_ad_accounts")
    op.drop_table("brand_ad_accounts")
    for column in ("min_purchases", "scale_roas", "min_spend", "lookback_days"):
        op.drop_column("brands", column)
    op.alter_column(
        "brands",
        "break_even_roas",
        existing_type=sa.Numeric(18, 6),
        type_=sa.Float(),
        postgresql_using="break_even_roas::double precision",
        existing_nullable=True,
    )
