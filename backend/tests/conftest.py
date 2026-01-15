"""Pytest configuration and fixtures for backend tests."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Create a mock database session.

    Returns a mock AsyncSession that can be used in place of a real database.
    """
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_enqueue_job() -> MagicMock:
    """Create a mock enqueue_job function.

    Returns a mock that can be used to verify job enqueueing.
    """
    mock_job = MagicMock()
    mock_job.id = "mock-job-id"
    return MagicMock(return_value=mock_job)


@pytest.fixture
async def client_with_mock_db(
    mock_db_session: MagicMock,
    mock_enqueue_job: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with mocked database and queue.

    This allows testing API endpoints without a real database or Redis connection.
    """

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.api.documents.enqueue_job", mock_enqueue_job):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client without database mocking.

    Use this for endpoints that don't require database access.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
