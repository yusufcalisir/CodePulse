"""Shared pytest fixtures for the backend testing suite."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession


# Helper to build mock database execute results
class MockResult:
    """Mock helper for SQLAlchemy Result objects."""

    def __init__(self, rows: list = None, scalar_rows: list = None) -> None:
        self._rows = rows or []
        self._scalar_rows = scalar_rows or []

    def all(self) -> list:
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def one(self):
        if not self._rows:
            raise Exception("No rows found for one()")
        return self._rows[0]

    def scalar_one(self):
        if not self._scalar_rows:
            raise Exception("No rows found for scalar_one()")
        return self._scalar_rows[0]

    def scalar_one_or_none(self):
        return self._scalar_rows[0] if self._scalar_rows else None

    def scalars(self):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = self._scalar_rows
        mock_scalars.first.return_value = (
            self._scalar_rows[0] if self._scalar_rows else None
        )
        mock_scalars.one.return_value = self._scalar_rows[0]
        mock_scalars.one_or_none.return_value = (
            self._scalar_rows[0] if self._scalar_rows else None
        )
        return mock_scalars


@pytest.fixture
def mock_settings() -> Settings:
    """Provide a settings instance with testing config."""
    return Settings(
        APP_NAME="CodePulseTest",
        DEBUG=True,
        GITHUB_TOKEN="ghp_test_token",
        DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
    )


@pytest.fixture
def mock_db() -> AsyncMock:
    """Provide a mock SQLAlchemy AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def app(mock_settings: Settings, mock_db: AsyncMock) -> FastAPI:
    """Provide the FastAPI application configured for testing."""
    test_app = create_app()

    # Override Settings
    test_app.dependency_overrides[get_settings] = lambda: mock_settings
    # Override Database session dependency
    test_app.dependency_overrides[get_db] = lambda: mock_db

    return test_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client for API endpoint testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"X-Org-Id": "test_org"}
    ) as ac:
        yield ac
