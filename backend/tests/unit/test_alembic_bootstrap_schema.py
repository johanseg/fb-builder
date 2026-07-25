from sqlalchemy import inspect, text

from app.database import engine
from app.database import SessionLocal
from app.models import Role
from init_db import seed_roles_and_permissions


def test_bootstrapped_schema_is_stamped_and_has_launch_constraints():
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert {"launch_jobs", "launch_targets", "launch_operations", "brand_ad_accounts", "meta_insight_daily"}.issubset(inspector.get_table_names())
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "c8d4e1f2a901"
        target_checks = {item["name"] for item in inspector.get_check_constraints("launch_targets")}
        operation_checks = {item["name"] for item in inspector.get_check_constraints("launch_operations")}
        assert "ck_launch_targets_status" in target_checks
        assert "ck_launch_operations_status" in operation_checks


def test_reporting_permissions_follow_least_privilege_role_matrix():
    seed_roles_and_permissions()
    db = SessionLocal()
    try:
        reporting = {
            role.name: {permission.name for permission in role.permissions if permission.name.startswith("reporting:")}
            for role in db.query(Role).filter(Role.name.in_(("viewer", "editor", "manager", "admin"))).all()
        }
    finally:
        db.close()
    assert reporting["viewer"] == {"reporting:read"}
    assert reporting["editor"] == {"reporting:read"}
    assert reporting["manager"] == {"reporting:read", "reporting:write", "reporting:sync"}
    assert reporting["admin"] == {"reporting:read", "reporting:write", "reporting:sync"}
