"""API Dependencies for tenant isolation and repository access verification."""

import logging
from fastapi import Header, HTTPException, status, Depends, Query, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.data_plane.storage.models.repository import Repository

logger = logging.getLogger(__name__)


async def get_org_id(
    x_org_id: str = Header(..., description="Organization ID for multi-tenant isolation")
) -> str:
    """FastAPI header dependency to retrieve the active organization ID."""
    return x_org_id


async def verify_repo_access(
    repo_id: int = Path(..., description="Repository ID"),
    x_org_id: str = Header(..., description="Organization ID for multi-tenant isolation"),
    db: AsyncSession = Depends(get_db),
) -> Repository:
    """FastAPI dependency to verify that a repository exists and belongs to the requesting tenant (path param)."""
    result = await db.execute(
        select(Repository).where(
            Repository.id == repo_id,
            Repository.org_id == x_org_id
        )
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found or access denied for organization {x_org_id}",
        )
    return repo


async def verify_repo_access_query(
    repo_id: int = Query(..., description="Repository ID"),
    x_org_id: str = Header(..., description="Organization ID for multi-tenant isolation"),
    db: AsyncSession = Depends(get_db),
) -> Repository:
    """FastAPI dependency to verify that a repository exists and belongs to the requesting tenant (query param)."""
    result = await db.execute(
        select(Repository).where(
            Repository.id == repo_id,
            Repository.org_id == x_org_id
        )
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found or access denied for organization {x_org_id}",
        )
    return repo

