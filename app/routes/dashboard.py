"""Dashboard: pipeline KPIs, funnel, and conversion rates."""
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models import (
    ACTIVE_STAGES,
    Candidate,
    FUNNEL_STAGES,
    Practice,
    STAGES,
)

dashboard_bp = Blueprint("dashboard", __name__)


def _stage_counts():
    rows = (
        db.session.query(Candidate.stage, func.count(Candidate.id))
        .group_by(Candidate.stage)
        .all()
    )
    return {stage: count for stage, count in rows}


def _funnel(counts):
    """Cumulative funnel: how many candidates reached *at least* each stage.

    Because the pipeline is sequential, a candidate currently in 'Interview'
    has, by definition, passed through Sourced/Contacted/Screening. 'Passed'
    candidates are off-ramps and excluded from the funnel reached-counts.
    """
    # Index of each funnel stage so we can count "reached at least here".
    order = {s: i for i, s in enumerate(FUNNEL_STAGES)}
    reached = []
    for i, stage in enumerate(FUNNEL_STAGES):
        total = 0
        for s, c in counts.items():
            if s in order and order[s] >= i:
                total += c
        reached.append({"stage": stage, "count": total})

    # Stage-to-stage conversion rate.
    for idx, entry in enumerate(reached):
        if idx == 0:
            entry["conversion"] = 100.0
        else:
            prev = reached[idx - 1]["count"]
            entry["conversion"] = round(100.0 * entry["count"] / prev, 1) if prev else 0.0
    return reached


@dashboard_bp.route("/")
@login_required
def index():
    counts = _stage_counts()
    total = sum(counts.values())
    active = sum(c for s, c in counts.items() if s in ACTIVE_STAGES)
    hired = counts.get("Hired", 0)
    passed = counts.get("Passed", 0)

    # Overall conversion = hired / everyone who entered the pipeline.
    overall_conversion = round(100.0 * hired / total, 1) if total else 0.0
    # Offer acceptance = hired / (hired + offers + passed-from-offer is unknown,
    # so use hired vs hired+offer as a simple acceptance proxy).
    offers = counts.get("Offer", 0)
    offer_accept = round(100.0 * hired / (hired + offers), 1) if (hired + offers) else 0.0

    funnel = _funnel(counts)

    kpis = {
        "total": total,
        "active": active,
        "hired": hired,
        "passed": passed,
        "overall_conversion": overall_conversion,
        "offer_accept": offer_accept,
        "open_practices": Practice.query.count(),
    }

    # Stage breakdown in pipeline order (includes Passed for the bar chart).
    stage_breakdown = [{"stage": s, "count": counts.get(s, 0)} for s in STAGES]

    # A few recently active candidates for the activity panel.
    recent = (
        Candidate.query.filter(Candidate.stage.in_(ACTIVE_STAGES))
        .order_by(Candidate.last_activity.desc())
        .limit(8)
        .all()
    )

    return render_template(
        "dashboard.html",
        kpis=kpis,
        funnel=funnel,
        stage_breakdown=stage_breakdown,
        recent=recent,
    )
