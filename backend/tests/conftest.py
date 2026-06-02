import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.deps import get_db
import app.modules.models  # noqa: F401 — register metadata
from app.main import app as fastapi_app

TEST_DATABASE_URL = "sqlite://"


@pytest.fixture
def db_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Session:
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def seed_catalog(db_session: Session) -> None:
    from app.modules.module_registry.service import ModuleRegistryService
    from app.modules.subscriptions.service import SubscriptionService

    from app.modules.industry_templates.service import IndustryTemplateService

    ModuleRegistryService(db_session).seed_definitions()
    SubscriptionService(db_session).seed_catalog()
    IndustryTemplateService(db_session).seed_templates()
    from app.modules.integrations.service import IntegrationService

    IntegrationService(db_session).seed_providers()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
