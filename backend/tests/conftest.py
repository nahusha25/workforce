import asyncio
import sys

import pytest
import pytest_asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app

# Test DB URL
TEST_DATABASE_URL = settings.DATABASE_URL + "_test"

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

from sqlalchemy import create_engine

# Sync engine for setup to avoid loop conflicts
TEST_DATABASE_URL_SYNC = TEST_DATABASE_URL.replace("postgresql+asyncpg", "postgresql+pg8000")

# Patch pg8000 to map all PostgreSQL class 23 (Integrity Constraint Violation) to IntegrityError
try:
    import pg8000.legacy
    _orig_execute = pg8000.legacy.Cursor.execute
    def _patched_execute(self, operation, args=(), stream=None):
        try:
            return _orig_execute(self, operation, args, stream)
        except pg8000.legacy.ProgrammingError as e:
            msg = e.args[0]
            if isinstance(msg, dict) and str(msg.get("C", "")).startswith("23"):
                raise pg8000.legacy.IntegrityError(msg) from e
            raise
    pg8000.legacy.Cursor.execute = _patched_execute
except ImportError:
    pass

engine_sync_test = create_engine(TEST_DATABASE_URL_SYNC, echo=False)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(engine_sync_test)
    yield
    Base.metadata.drop_all(engine_sync_test)
    engine_sync_test.dispose()

@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session

from sqlalchemy.orm import sessionmaker

TestingSessionLocalSync = sessionmaker(autocommit=False, autoflush=False, bind=engine_sync_test)

@pytest.fixture
def sync_db_session():
    with TestingSessionLocalSync() as session:
        yield session

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    yield TestClient(app)
