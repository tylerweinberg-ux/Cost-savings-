"""Practice list and detail, including linked candidates."""
from flask import Blueprint, render_template
from flask_login import login_required

from app.models import ACTIVE_STAGES, Candidate, Practice

practices_bp = Blueprint("practices", __name__, url_prefix="/practices")


@practices_bp.route("/")
@login_required
def list_practices():
    practices = Practice.query.order_by(Practice.name).all()
    # Annotate with linked + active candidate counts for the table.
    summary = []
    for p in practices:
        linked = p.candidates
        active = [c for c in linked if c.stage in ACTIVE_STAGES]
        hired = [c for c in linked if c.stage == "Hired"]
        summary.append(
            {
                "practice": p,
                "linked": len(linked),
                "active": len(active),
                "hired": len(hired),
            }
        )
    return render_template("practices/list.html", summary=summary)


@practices_bp.route("/<int:practice_id>")
@login_required
def detail(practice_id):
    practice = Practice.query.get_or_404(practice_id)
    candidates = sorted(
        practice.candidates, key=lambda c: c.last_activity, reverse=True
    )
    active = [c for c in candidates if c.stage in ACTIVE_STAGES]
    return render_template(
        "practices/detail.html",
        practice=practice,
        candidates=candidates,
        active_count=len(active),
    )
