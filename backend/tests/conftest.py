# =============================================================================
# PROJECT NEXUS AI - Pytest Configuration
# =============================================================================
# Configure pytest-asyncio and test fixtures.
# =============================================================================

import asyncio
import pytest

from app.db.database import AsyncSessionLocal, engine
from app.models import Base


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    """Initialize the database before all tests."""
    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.get_event_loop().run_until_complete(_init())
    yield


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


pytestmark = pytest.mark.asyncio
