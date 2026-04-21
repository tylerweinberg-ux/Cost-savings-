"""ETL pipeline: pull data from Zenoti API → upsert into the data warehouse."""
import logging
from datetime import datetime, date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.zenoti.client import ZenotiClient
from app.warehouse.models import (
    DimCenter, DimGuest, DimEmployee, DimService,
    FactAppointment, FactInvoice, FactInvoiceItem, SyncLog,
)

logger = logging.getLogger(__name__)


def _upsert(model, data: dict) -> Any:
    """Build a SQLite INSERT OR REPLACE statement."""
    stmt = sqlite_insert(model).values(**data)
    return stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={k: v for k, v in data.items() if k != "id"},
    )


# ------------------------------------------------------------------ #
# Individual entity sync functions
# ------------------------------------------------------------------ #

async def sync_centers(session: AsyncSession, client: ZenotiClient) -> int:
    raw = await client.get_centers()
    for c in raw:
        await session.execute(_upsert(DimCenter, {
            "id": c.get("id") or c.get("center_id"),
            "name": c.get("name"),
            "code": c.get("code"),
            "city": c.get("address", {}).get("city") if isinstance(c.get("address"), dict) else None,
            "country": c.get("address", {}).get("country") if isinstance(c.get("address"), dict) else None,
            "currency_id": c.get("currency_id"),
            "time_zone": c.get("time_zone"),
            "synced_at": datetime.utcnow(),
        }))
    await session.commit()
    return len(raw)


async def sync_guests(session: AsyncSession, client: ZenotiClient, center_id: str) -> int:
    raw = await client.get_guests(center_id)
    for g in raw:
        await session.execute(_upsert(DimGuest, {
            "id": g.get("id"),
            "first_name": g.get("personal_info", {}).get("first_name") or g.get("first_name"),
            "last_name": g.get("personal_info", {}).get("last_name") or g.get("last_name"),
            "email": g.get("personal_info", {}).get("email") or g.get("email"),
            "mobile": g.get("personal_info", {}).get("mobile_phone", {}).get("number") or g.get("mobile"),
            "gender": g.get("personal_info", {}).get("gender"),
            "date_of_birth": g.get("personal_info", {}).get("date_of_birth"),
            "center_id": center_id,
            "created_date": g.get("created_date"),
            "synced_at": datetime.utcnow(),
        }))
    await session.commit()
    return len(raw)


async def sync_employees(session: AsyncSession, client: ZenotiClient, center_id: str) -> int:
    raw = await client.get_employees(center_id)
    for e in raw:
        await session.execute(_upsert(DimEmployee, {
            "id": e.get("id"),
            "first_name": e.get("personal_info", {}).get("first_name") or e.get("first_name"),
            "last_name": e.get("personal_info", {}).get("last_name") or e.get("last_name"),
            "email": e.get("personal_info", {}).get("email") or e.get("email"),
            "code": e.get("code"),
            "designation": e.get("designation", {}).get("name") if isinstance(e.get("designation"), dict) else e.get("designation"),
            "center_id": center_id,
            "synced_at": datetime.utcnow(),
        }))
    await session.commit()
    return len(raw)


async def sync_services(session: AsyncSession, client: ZenotiClient, center_id: str) -> int:
    raw = await client.get_services(center_id)
    for s in raw:
        price_info = s.get("price") or {}
        base_price = None
        if isinstance(price_info, dict):
            base_price = price_info.get("sales_price") or price_info.get("price")
        await session.execute(_upsert(DimService, {
            "id": s.get("id"),
            "name": s.get("name"),
            "code": s.get("code"),
            "category_name": s.get("category_name") or (s.get("category") or {}).get("name"),
            "duration_minutes": s.get("duration") or s.get("min_duration"),
            "base_price": base_price,
            "center_id": center_id,
            "synced_at": datetime.utcnow(),
        }))
    await session.commit()
    return len(raw)


async def sync_appointments(
    session: AsyncSession, client: ZenotiClient, center_id: str, start_date: str, end_date: str
) -> int:
    raw = await client.get_appointments(center_id, start_date, end_date)
    count = 0
    for appt in raw:
        appt_id = appt.get("id")
        services = appt.get("appointment_services") or appt.get("services") or []
        # Flatten: one row per appointment-service pair; use appt_id if no services
        if not services:
            services = [{}]
        for svc in services:
            row_id = f"{appt_id}_{svc.get('id', 'none')}" if svc else appt_id
            await session.execute(_upsert(FactAppointment, {
                "id": row_id,
                "center_id": center_id,
                "appointment_group_id": appt.get("appointment_group_id"),
                "guest_id": svc.get("guest_id") or appt.get("guest_id"),
                "service_id": svc.get("service_id") or svc.get("id"),
                "therapist_id": svc.get("therapist_id"),
                "start_time": svc.get("start_time") or appt.get("start_time"),
                "end_time": svc.get("end_time") or appt.get("end_time"),
                "status": appt.get("status"),
                "price": svc.get("price"),
                "created_date": appt.get("created_date"),
                "synced_at": datetime.utcnow(),
            }))
            count += 1
    await session.commit()
    return count


async def sync_invoices(
    session: AsyncSession, client: ZenotiClient, center_id: str, start_date: str, end_date: str
) -> int:
    raw = await client.get_invoices(center_id, start_date, end_date)
    count = 0
    for inv in raw:
        inv_id = inv.get("id")
        await session.execute(_upsert(FactInvoice, {
            "id": inv_id,
            "invoice_number": inv.get("invoice_number"),
            "center_id": center_id,
            "guest_id": inv.get("guest_id"),
            "appointment_id": inv.get("appointment_id"),
            "total_price": inv.get("total_price") or inv.get("sub_total"),
            "total_tax": inv.get("total_tax"),
            "total_discount": inv.get("total_discount"),
            "final_price": inv.get("final_price") or inv.get("total"),
            "status": inv.get("status"),
            "created_date": inv.get("created_date"),
            "synced_at": datetime.utcnow(),
        }))
        # Sync line items
        items = inv.get("invoice_items") or inv.get("items") or []
        for item in items:
            stmt = sqlite_insert(FactInvoiceItem).values(
                invoice_id=inv_id,
                item_id=item.get("id"),
                item_type=item.get("item_type"),
                name=item.get("name"),
                quantity=item.get("quantity", 1),
                unit_price=item.get("price") or item.get("unit_price"),
                final_price=item.get("final_price"),
                discount=item.get("discount"),
                tax=item.get("tax"),
            )
            await session.execute(stmt)
        count += 1
    await session.commit()
    return count


# ------------------------------------------------------------------ #
# Orchestrated full sync
# ------------------------------------------------------------------ #

async def run_full_sync(
    session: AsyncSession,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Pull all entities for all centers and load into the warehouse."""
    if not end_date:
        end_date = date.today().isoformat()
    if not start_date:
        start_date = (date.today() - timedelta(days=90)).isoformat()

    results: dict[str, Any] = {}

    async with ZenotiClient() as client:
        # 1. Centers
        log = SyncLog(entity="centers", status="running")
        session.add(log)
        await session.commit()
        try:
            n = await sync_centers(session, client)
            log.records_synced = n
            log.status = "success"
            log.finished_at = datetime.utcnow()
            await session.commit()
            results["centers"] = n
        except Exception as exc:
            log.status = "error"
            log.error_message = str(exc)
            log.finished_at = datetime.utcnow()
            await session.commit()
            raise

        # 2. Per-center entities
        center_rows = (await session.execute(select(DimCenter))).scalars().all()
        for center in center_rows:
            cid = center.id
            for entity, fn, kwargs in [
                ("guests", sync_guests, {"center_id": cid}),
                ("employees", sync_employees, {"center_id": cid}),
                ("services", sync_services, {"center_id": cid}),
                ("appointments", sync_appointments, {"center_id": cid, "start_date": start_date, "end_date": end_date}),
                ("invoices", sync_invoices, {"center_id": cid, "start_date": start_date, "end_date": end_date}),
            ]:
                log = SyncLog(entity=entity, center_id=cid, start_date=start_date, end_date=end_date, status="running")
                session.add(log)
                await session.commit()
                try:
                    n = await fn(session, client, **kwargs)
                    log.records_synced = n
                    log.status = "success"
                    log.finished_at = datetime.utcnow()
                    await session.commit()
                    results.setdefault(entity, 0)
                    results[entity] += n
                    logger.info("Synced %d %s for center %s", n, entity, cid)
                except Exception as exc:
                    log.status = "error"
                    log.error_message = str(exc)
                    log.finished_at = datetime.utcnow()
                    await session.commit()
                    logger.error("Error syncing %s for center %s: %s", entity, cid, exc)
                    results.setdefault(f"{entity}_error", []).append(str(exc))

    return results
