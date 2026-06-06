"""Candidate list, profile, notes, and stage/practice updates."""
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.models import ACTIVE_STAGES, Candidate, Note, Practice, STAGES, User

candidates_bp = Blueprint("candidates", __name__, url_prefix="/candidates")


@candidates_bp.route("/")
@login_required
def list_candidates():
    q = request.args.get("q", "").strip()
    stage = request.args.get("stage", "").strip()
    practice_id = request.args.get("practice", "").strip()
    active_only = request.args.get("active") == "1"

    query = Candidate.query

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Candidate.first_name.ilike(like),
                Candidate.last_name.ilike(like),
                Candidate.email.ilike(like),
                Candidate.current_location.ilike(like),
            )
        )
    if stage:
        query = query.filter(Candidate.stage == stage)
    if active_only:
        query = query.filter(Candidate.stage.in_(ACTIVE_STAGES))
    if practice_id.isdigit():
        query = query.filter(Candidate.practice_id == int(practice_id))

    candidates = query.order_by(
        Candidate.last_activity.desc(), Candidate.last_name.asc()
    ).all()

    return render_template(
        "candidates/list.html",
        candidates=candidates,
        stages=STAGES,
        practices=Practice.query.order_by(Practice.name).all(),
        filters={
            "q": q,
            "stage": stage,
            "practice": practice_id,
            "active": active_only,
        },
        total=Candidate.query.count(),
    )


@candidates_bp.route("/<int:candidate_id>")
@login_required
def detail(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    return render_template(
        "candidates/detail.html",
        candidate=candidate,
        stages=STAGES,
        practices=Practice.query.order_by(Practice.name).all(),
        team=User.query.order_by(User.name).all(),
    )


@candidates_bp.route("/<int:candidate_id>/notes", methods=["POST"])
@login_required
def add_note(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    body = request.form.get("body", "").strip()
    if body:
        note = Note(candidate_id=candidate.id, author_id=current_user.id, body=body)
        candidate.last_activity = note.created_at
        db.session.add(note)
        db.session.commit()
        flash("Note added.", "success")
    else:
        flash("Note cannot be empty.", "warning")
    return redirect(url_for("candidates.detail", candidate_id=candidate.id))


@candidates_bp.route("/<int:candidate_id>/update", methods=["POST"])
@login_required
def update(candidate_id):
    """Update stage, practice assignment, owner, or rating."""
    from datetime import datetime

    candidate = Candidate.query.get_or_404(candidate_id)

    stage = request.form.get("stage")
    if stage in STAGES:
        candidate.stage = stage

    practice_id = request.form.get("practice_id", "")
    candidate.practice_id = int(practice_id) if practice_id.isdigit() else None

    owner_id = request.form.get("owner_id", "")
    candidate.owner_id = int(owner_id) if owner_id.isdigit() else None

    rating = request.form.get("rating", "")
    if rating.isdigit() and 1 <= int(rating) <= 5:
        candidate.rating = int(rating)

    candidate.last_activity = datetime.utcnow()
    db.session.commit()
    flash("Candidate updated.", "success")
    return redirect(url_for("candidates.detail", candidate_id=candidate.id))
