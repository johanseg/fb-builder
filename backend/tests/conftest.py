import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Tests must never silently select an app, Railway, or production database.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "").strip()
if not TEST_DATABASE_URL:
    raise ValueError("TEST_DATABASE_URL is required for tests")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-change-in-production"

# Do not allow a developer's .env provider credentials into tests. config.py may
# load that file during app import, but dotenv does not override explicit values.
for _provider_var in (
    "GEMINI_API_KEY",
    "FAL_AI_API_KEY",
    "KIE_AI_API_KEY",
    "FACEBOOK_ACCESS_TOKEN",
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
    "R2_PUBLIC_URL",
):
    os.environ[_provider_var] = ""

from app.main import app
from app.database import get_db
from app.models import Role, User
from app.core.security import get_password_hash
from app.core.rate_limit import limiter

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Tests require a separately migrated database; never create schema implicitly."""
    with engine.connect() as connection:
        migrated = connection.execute(text("SELECT to_regclass('public.alembic_version')")).scalar()
    if not migrated:
        raise RuntimeError("Run `alembic upgrade head` against TEST_DATABASE_URL before pytest")


@pytest.fixture(scope="function")
def db_session():
    """Create an isolated database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def disable_rate_limits():
    """Keep ordinary tests isolated from SlowAPI's process-wide counters."""
    was_enabled = limiter.enabled
    limiter.enabled = False
    limiter.reset()
    try:
        yield
    finally:
        limiter.reset()
        limiter.enabled = was_enabled


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user with admin role and all permissions."""
    from app.models import Permission

    # Get or create permissions
    def get_or_create_permission(name, description):
        perm = db_session.query(Permission).filter(Permission.name == name).first()
        if not perm:
            perm = Permission(name=name, description=description)
            db_session.add(perm)
        return perm

    # Create all permissions needed for tests
    all_permissions = [
        ("brands:read", "Read brands"),
        ("campaigns:write", "Write campaigns"),
        ("campaigns:read", "Read campaigns"),
        ("campaigns:activate", "Activate campaigns"),
        ("campaigns:delete", "Delete campaigns"),
        ("ads:read", "Read ads"),
        ("ads:write", "Write ads"),
        ("ads:delete", "Delete ads"),
        ("brands:write", "Write brands"),
        ("brands:delete", "Delete brands"),
        ("products:read", "Read products"),
        ("products:write", "Write products"),
        ("products:delete", "Delete products"),
        ("profiles:read", "Read profiles"),
        ("profiles:write", "Write profiles"),
        ("profiles:delete", "Delete profiles"),
        ("templates:read", "Read templates"),
        ("templates:write", "Write templates"),
        ("templates:delete", "Delete templates"),
        ("users:read", "Read users"),
        ("users:write", "Write users"),
        ("prompts:read", "Read prompts"),
        ("prompts:write", "Write prompts"),
        ("prompts:delete", "Delete prompts"),
        ("ad_styles:read", "Read ad styles"),
        ("ad_styles:write", "Write ad styles"),
        ("ad_styles:delete", "Delete ad styles"),
        ("research:read", "Read research"),
        ("research:write", "Write research"),
        ("research:admin", "Administer research"),
        ("reporting:read", "Read reporting"),
        ("reporting:write", "Write reporting"),
        ("reporting:sync", "Sync reporting"),
    ]

    permissions = []
    for name, desc in all_permissions:
        perm = get_or_create_permission(name, desc)
        permissions.append(perm)
    db_session.commit()

    # Get or create admin role with all permissions
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(name="admin", description="Administrator")
        for perm in permissions:
            admin_role.permissions.append(perm)
        db_session.add(admin_role)
        db_session.commit()
    else:
        # Ensure admin role has all permissions
        for perm in permissions:
            if perm not in admin_role.permissions:
                admin_role.permissions.append(perm)
        db_session.commit()

    # Clean up any existing test user
    existing_user = db_session.query(User).filter(User.email == "test@example.com").first()
    if existing_user:
        from app.models import RefreshToken
        db_session.query(RefreshToken).filter(RefreshToken.user_id == existing_user.id).delete()
        db_session.delete(existing_user)
        db_session.commit()

    # Create test user
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        name="Test User",
        is_active=True
    )
    user.roles.append(admin_role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user."""
    response = client.post(
        "/api/v1/auth/login/json",
        json={"email": test_user.email, "password": "testpassword"}
    )
    if response.status_code != 200:
        print(f"Login failed: {response.status_code} - {response.text}")
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_facebook_service(client):
    """Mock FacebookService for testing."""
    from app.api.v1.facebook import get_facebook_service

    service = MagicMock()
    service.api = MagicMock()

    def override_get_facebook_service():
        return service

    app.dependency_overrides[get_facebook_service] = override_get_facebook_service
    yield service
    # Clean up the override
    if get_facebook_service in app.dependency_overrides:
        del app.dependency_overrides[get_facebook_service]
