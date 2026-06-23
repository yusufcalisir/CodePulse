"""Repository management endpoints."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, get_db
from app.data_plane.storage.models.repository import Repository
from app.data_plane.storage.models.sync_log import SyncLog
from app.schemas.repository import (
    RepositoryListResponse,
    RepositoryResponse,
    SyncRequest,
    SyncStatusResponse,
)
from app.data_plane.storage.storage_manager import StorageManager
from app.data_plane.storage.replay_service import ReplayService
from app.intelligence_plane.api.dependencies import get_org_id, verify_repo_access

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    org_id: str = Depends(get_org_id),
    db: AsyncSession = Depends(get_db),
):
    """List all tracked repositories."""
    result = await db.execute(
        select(Repository)
        .where(Repository.org_id == org_id)
        .order_by(Repository.updated_at.desc())
    )
    repos = result.scalars().all()

    return RepositoryListResponse(
        repositories=[RepositoryResponse.model_validate(r) for r in repos],
        count=len(repos),
    )


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo: Repository = Depends(verify_repo_access),
):
    """Get a single repository by ID."""
    return RepositoryResponse.model_validate(repo)


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_repository(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    org_id: str = Depends(get_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a full sync for a repository.

    This starts the sync as a background task and returns immediately.
    """
    full_name = request.full_name

    # Validate format
    if "/" not in full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="full_name must be in 'owner/repo' format",
        )

    # Check if sync is already running for this repo
    result = await db.execute(
        select(Repository).where(
            Repository.full_name == full_name,
            Repository.org_id == org_id
        )
    )
    existing_repo = result.scalar_one_or_none()

    if existing_repo:
        running_check = await db.execute(
            select(SyncLog).where(
                SyncLog.repo_id == existing_repo.id,
                SyncLog.status == "running",
            )
        )
        if running_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Sync already in progress for this repository",
            )

    # Start background sync
    background_tasks.add_task(_run_sync, full_name, org_id)

    return {
        "message": f"Sync started for {full_name}",
        "full_name": full_name,
        "status": "running",
    }


@router.get("/{repo_id}/sync-status", response_model=SyncStatusResponse | None)
async def get_sync_status(
    repo: Repository = Depends(verify_repo_access),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest sync status for a repository."""
    result = await db.execute(
        select(SyncLog)
        .where(SyncLog.repo_id == repo.id)
        .order_by(SyncLog.started_at.desc())
        .limit(1)
    )
    sync_log = result.scalar_one_or_none()

    if not sync_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No sync history for repository {repo.id}",
        )

    return SyncStatusResponse(
        sync_id=sync_log.id,
        repo_id=sync_log.repo_id,
        status=sync_log.status,
        pr_count=sync_log.pr_count,
        started_at=sync_log.started_at,
        finished_at=sync_log.finished_at,
        error=sync_log.error,
    )


async def _run_sync(full_name: str, org_id: str) -> None:
    """Background task to run a full repository sync.

    Creates its own database session since background tasks
    run outside the request lifecycle.
    """
    async with async_session_factory() as session:
        try:
            storage_manager = StorageManager(db=session)
            await storage_manager.initial_sync(full_name, org_id)
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Background sync failed for %s: %s", full_name, e)
        finally:
            await storage_manager.close()


@router.post("/{repo_id}/replay", status_code=status.HTTP_200_OK)
async def replay_repository_events(
    repo: Repository = Depends(verify_repo_access),
    db: AsyncSession = Depends(get_db),
):
    """Replays events sequentially to reconstruct database state tables for a repository."""
    try:
        replayed_count = await ReplayService.replay_repository_events(db, repo.id)
        await db.commit()
        return {
            "message": f"Successfully replayed {replayed_count} events for repository {repo.id}",
            "replayed_count": replayed_count,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        logger.error("Event replay failed for repository %d: %s", repo.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to replay events: {str(e)}",
        )

