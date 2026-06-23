"""Pydantic schemas for repository endpoints."""

from datetime import datetime

from pydantic import BaseModel


class RepositoryBase(BaseModel):
    """Base schema for repository data."""

    github_id: int
    name: str
    full_name: str
    org: str | None = None
    default_branch: str = "main"


class RepositoryResponse(RepositoryBase):
    """Response schema for a repository."""

    id: int
    synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RepositoryListResponse(BaseModel):
    """Response schema for listing repositories."""

    repositories: list[RepositoryResponse]
    count: int


class SyncRequest(BaseModel):
    """Request schema for triggering a repository sync."""

    full_name: str  # e.g. "org/repo"


class SyncStatusResponse(BaseModel):
    """Response schema for sync status."""

    sync_id: int
    repo_id: int
    status: str  # running, completed, failed
    pr_count: int
    started_at: datetime
    finished_at: datetime | None = None
    error: str | None = None

    model_config = {"from_attributes": True}
