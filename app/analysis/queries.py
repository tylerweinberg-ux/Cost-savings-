"""Analysis queries that run directly against the data warehouse."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def revenue_by_period(session: AsyncSession, period: str = "month", center_id: str | None = None) -> list[dict]:
    """Aggregate invoice revenue grouped by day / week / month."""
    fmt = {"day": "%Y-%m-%d", "week": "%Y-W%W", "month": "%Y-%m"}.get(period, "%Y-%m")
    center_filter = "AND i.center_id = :cid" if center_id else ""
    sql = text(f"""
        SELECT
            strftime('{fmt}', i.created_date) AS period,
            COUNT(*)                           AS invoice_count,
            ROUND(SUM(i.final_price), 2)       AS total_revenue,
            ROUND(SUM(i.total_discount), 2)    AS total_discount,
            ROUND(SUM(i.total_tax), 2)         AS total_tax
        FROM fact_invoices i
        WHERE i.status != 5
          AND i.created_date IS NOT NULL
          {center_filter}
        GROUP BY 1
        ORDER BY 1
    """)
    result = await session.execute(sql, {"cid": center_id} if center_id else {})
    return [dict(row._mapping) for row in result]


async def top_services(session: AsyncSession, limit: int = 10, center_id: str | None = None) -> list[dict]:
    center_filter = "AND ii.invoice_id IN (SELECT id FROM fact_invoices WHERE center_id = :cid)" if center_id else ""
    sql = text(f"""
        SELECT
            COALESCE(ds.name, ii.name, 'Unknown') AS service_name,
            ds.category_name,
            COUNT(*)                               AS bookings,
            ROUND(SUM(ii.final_price), 2)          AS total_revenue,
            ROUND(AVG(ii.final_price), 2)          AS avg_price
        FROM fact_invoice_items ii
        LEFT JOIN dim_services ds ON ds.id = ii.item_id
        WHERE ii.item_type = 1
          {center_filter}
        GROUP BY 1, 2
        ORDER BY total_revenue DESC
        LIMIT :lim
    """)
    result = await session.execute(sql, {"lim": limit, "cid": center_id} if center_id else {"lim": limit})
    return [dict(row._mapping) for row in result]


async def guest_retention(session: AsyncSession, center_id: str | None = None) -> dict:
    """New vs returning guests based on visit count."""
    center_filter = "AND center_id = :cid" if center_id else ""
    sql = text(f"""
        WITH visit_counts AS (
            SELECT guest_id, COUNT(DISTINCT id) AS visits
            FROM fact_invoices
            WHERE guest_id IS NOT NULL
              {center_filter}
            GROUP BY guest_id
        )
        SELECT
            SUM(CASE WHEN visits = 1 THEN 1 ELSE 0 END) AS new_guests,
            SUM(CASE WHEN visits > 1  THEN 1 ELSE 0 END) AS returning_guests,
            COUNT(*)                                      AS total_guests,
            ROUND(AVG(visits), 2)                         AS avg_visits_per_guest
        FROM visit_counts
    """)
    result = await session.execute(sql, {"cid": center_id} if center_id else {})
    row = result.fetchone()
    return dict(row._mapping) if row else {}


async def employee_utilization(session: AsyncSession, center_id: str | None = None) -> list[dict]:
    center_filter = "AND fa.center_id = :cid" if center_id else ""
    sql = text(f"""
        SELECT
            COALESCE(de.first_name || ' ' || de.last_name, 'Unknown') AS therapist_name,
            de.designation,
            COUNT(fa.id)                                               AS appointments,
            SUM(CASE WHEN fa.status = 3 THEN 1 ELSE 0 END)            AS completed,
            SUM(CASE WHEN fa.status = 4 THEN 1 ELSE 0 END)            AS no_shows,
            SUM(CASE WHEN fa.status = 5 THEN 1 ELSE 0 END)            AS cancelled,
            ROUND(SUM(fa.price), 2)                                    AS total_revenue
        FROM fact_appointments fa
        LEFT JOIN dim_employees de ON de.id = fa.therapist_id
        WHERE fa.therapist_id IS NOT NULL
          {center_filter}
        GROUP BY fa.therapist_id
        ORDER BY completed DESC
    """)
    result = await session.execute(sql, {"cid": center_id} if center_id else {})
    return [dict(row._mapping) for row in result]


async def cost_savings_summary(session: AsyncSession, center_id: str | None = None) -> dict:
    """Discount vs full-price analysis to quantify cost savings passed to guests."""
    center_filter = "AND i.center_id = :cid" if center_id else ""
    sql = text(f"""
        SELECT
            ROUND(SUM(i.total_price), 2)    AS gross_revenue,
            ROUND(SUM(i.total_discount), 2) AS total_discounts_given,
            ROUND(SUM(i.final_price), 2)    AS net_revenue,
            ROUND(SUM(i.total_tax), 2)      AS total_tax_collected,
            COUNT(*)                        AS total_invoices,
            ROUND(
                100.0 * SUM(i.total_discount) / NULLIF(SUM(i.total_price), 0), 2
            )                               AS discount_rate_pct
        FROM fact_invoices i
        WHERE i.status != 5
          {center_filter}
    """)
    result = await session.execute(sql, {"cid": center_id} if center_id else {})
    row = result.fetchone()
    return dict(row._mapping) if row else {}


async def booking_trends(session: AsyncSession, center_id: str | None = None) -> list[dict]:
    """Day-of-week booking patterns."""
    center_filter = "AND center_id = :cid" if center_id else ""
    day_names = "case cast(strftime('%w', start_time) as integer) when 0 then 'Sunday' when 1 then 'Monday' when 2 then 'Tuesday' when 3 then 'Wednesday' when 4 then 'Thursday' when 5 then 'Friday' else 'Saturday' end"
    sql = text(f"""
        SELECT
            {day_names}                              AS day_of_week,
            cast(strftime('%w', start_time) as integer) AS day_num,
            COUNT(*)                                  AS total_appointments,
            SUM(CASE WHEN status = 3 THEN 1 ELSE 0 END) AS completed,
            SUM(CASE WHEN status = 5 THEN 1 ELSE 0 END) AS cancelled
        FROM fact_appointments
        WHERE start_time IS NOT NULL
          {center_filter}
        GROUP BY day_num
        ORDER BY day_num
    """)
    result = await session.execute(sql, {"cid": center_id} if center_id else {})
    return [dict(row._mapping) for row in result]


async def warehouse_summary(session: AsyncSession) -> dict:
    """Row counts for all warehouse tables."""
    tables = ["dim_centers", "dim_guests", "dim_employees", "dim_services",
              "fact_appointments", "fact_invoices", "fact_invoice_items"]
    counts = {}
    for table in tables:
        result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
        counts[table] = result.scalar()
    return counts
