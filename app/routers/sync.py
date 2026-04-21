"""Routes for triggering and monitoring data sync jobs."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.warehouse.database import get_db
from app.warehouse.models import SyncLog
from app.warehouse.etl import run_full_sync

router = APIRouter(prefix="/sync", tags=["sync"])

_sync_running = False


async def _do_sync(start_date: str, end_date: str):
    global _sync_running
    from app.warehouse.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            await run_full_sync(session, start_date=start_date, end_date=end_date)
        finally:
            _sync_running = False


@router.post("/")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """Kick off a full ETL sync in the background."""
    global _sync_running
    if _sync_running:
        raise HTTPException(status_code=409, detail="A sync is already running.")
    _sync_running = True
    sd = start_date or (date.today() - timedelta(days=90)).isoformat()
    ed = end_date or date.today().isoformat()
    background_tasks.add_task(_do_sync, sd, ed)
    return {"status": "started", "start_date": sd, "end_date": ed}


@router.get("/status")
async def sync_status(db: AsyncSession = Depends(get_db)):
    """Return the last 20 sync log entries."""
    result = await db.execute(
        select(SyncLog).order_by(desc(SyncLog.started_at)).limit(20)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "entity": log.entity,
            "center_id": log.center_id,
            "start_date": log.start_date,
            "end_date": log.end_date,
            "records_synced": log.records_synced,
            "status": log.status,
            "error_message": log.error_message,
            "started_at": log.started_at,
            "finished_at": log.finished_at,
        }
        for log in logs
    ]


@router.get("/running")
async def is_running():
    return {"running": _sync_running}
