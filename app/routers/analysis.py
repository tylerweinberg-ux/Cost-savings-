"""Analysis routes — all queries hit the local data warehouse."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.warehouse.database import get_db
from app.analysis import (
    revenue_by_period, top_services, guest_retention,
    employee_utilization, cost_savings_summary, booking_trends,
    warehouse_summary,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/summary")
async def warehouse_overview(db: AsyncSession = Depends(get_db)):
    return await warehouse_summary(db)


@router.get("/revenue")
async def revenue(
    period: str = Query("month", enum=["day", "week", "month"]),
    center_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await revenue_by_period(db, period=period, center_id=center_id)


@router.get("/services/top")
async def services_top(
    limit: int = Query(10, ge=1, le=100),
    center_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await top_services(db, limit=limit, center_id=center_id)


@router.get("/guests/retention")
async def guests_retention(
    center_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await guest_retention(db, center_id=center_id)


@router.get("/employees/utilization")
async def employees_util(
    center_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await employee_utilization(db, center_id=center_id)


@router.get("/cost-savings")
async def cost_savings(
    center_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await cost_savings_summary(db, center_id=center_id)


@router.get("/booking-trends")
async def booking_trends_route(
    center_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await booking_trends(db, center_id=center_id)
