import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from uuid import uuid4
from datetime import datetime

# Cấu hình đường dẫn để có thể import trực tiếp từ thư mục backend
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'api-service'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
from app.api.dependencies.deps import get_db, get_current_active_user, get_current_admin_user
from app.core.database import Base
from app.models.user import AppUser

# Setup in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    # Import all models to ensure they are registered with Base.metadata
    from app.models import Analytics, AppUser, Conversation, Message, Document, Rating, SystemLog, UserActivity
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def mock_user():
    return AppUser(
        id=uuid4(),
        email="test@example.com",
        role="user",
        is_active=True,
        created_at=datetime.now()
    )

@pytest.fixture
def mock_admin():
    return AppUser(
        id=uuid4(),
        email="admin@example.com",
        role="admin",
        is_active=True,
        created_at=datetime.now()
    )

@pytest.fixture
def authenticated_client(client, mock_user):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    yield client
    if get_current_active_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_active_user]

@pytest.fixture
def admin_client(client, mock_admin):
    app.dependency_overrides[get_current_active_user] = lambda: mock_admin
    app.dependency_overrides[get_current_admin_user] = lambda: mock_admin
    yield client
    if get_current_active_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_active_user]
    if get_current_admin_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_admin_user]
