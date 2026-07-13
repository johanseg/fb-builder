import os
from unittest.mock import MagicMock

from dotenv import load_dotenv
load_dotenv()

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Prefer an explicit test URL, then Railway's externally reachable Postgres URL,
# then the app DATABASE_URL for in-platform test runs.
TEST_DATABASE_URL = (
    os.getenv("TEST_DATABASE_URL")
    or os.getenv("DATABASE_PUBLIC_URL")
    or os.getenv("DATABASE_URL")
    or ""
).strip()
if not TEST_DATABASE_URL:
    raise ValueError("DATABASE_URL or TEST_DATABASE_URL environment variable required for tests")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-change-in-production")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")

from app.main import app
from app.database import Base, get_db
from app.models import Role, User
from app.core.security import get_password_hash

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initialize database tables once for the entire test session."""
    Base.metadata.create_all(bind=engine)


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
        ("campaigns:write", "Write campaigns"),
        ("ads:write", "Write ads"),
        ("ads:delete", "Delete ads"),
        ("brands:write", "Write brands"),
        ("brands:delete", "Delete brands"),
        ("products:write", "Write products"),
        ("products:delete", "Delete products"),
        ("profiles:write", "Write profiles"),
        ("profiles:delete", "Delete profiles"),
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
