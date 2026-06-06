"""Database models for the recruiting pipeline.

The schema is intentionally close to a CRM/Salesforce shape so it can be
synced later:
    Candidate  -> Salesforce Contact / Lead
    Practice   -> Salesforce Account
    Note       -> Salesforce Task / Note
"""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

# Ordered recruiting pipeline. Order matters for the funnel + conversion math.
STAGES = [
    "Sourced",
    "Contacted",
    "Screening",
    "Interview",
    "Offer",
    "Hired",
    "Passed",  # terminal: declined / not moving forward
]

# A candidate is "active" when they are in-process (not yet sourced-only,
# hired, or passed).
ACTIVE_STAGES = {"Contacted", "Screening", "Interview", "Offer"}

# Stages that count toward the conversion funnel, in order. "Passed" is a
# terminal off-ramp and is excluded from the funnel itself.
FUNNEL_STAGES = ["Sourced", "Contacted", "Screening", "Interview", "Offer", "Hired"]


class User(UserMixin, db.Model):
    """A member of the recruiting team."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(40), nullable=False, default="Recruiter")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owned_candidates = db.relationship("Candidate", back_populates="owner")
    notes = db.relationship("Note", back_populates="author")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


class Practice(db.Model):
    """A dental/oral-surgery practice a candidate could be placed at."""

    __tablename__ = "practices"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    city = db.Column(db.String(80))
    state = db.Column(db.String(40))
    region = db.Column(db.String(40))
    num_providers = db.Column(db.Integer, default=0)
    open_roles = db.Column(db.Integer, default=1)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    candidates = db.relationship("Candidate", back_populates="practice")

    @property
    def location(self):
        parts = [p for p in (self.city, self.state) if p]
        return ", ".join(parts)

    def __repr__(self):
        return f"<Practice {self.name}>"


class Candidate(db.Model):
    """An oral surgeon candidate moving through the pipeline."""

    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(160), index=True)
    phone = db.Column(db.String(40))

    specialty = db.Column(db.String(120), default="Oral & Maxillofacial Surgery")
    dental_school = db.Column(db.String(160))
    grad_year = db.Column(db.Integer)
    years_experience = db.Column(db.Integer, default=0)
    current_location = db.Column(db.String(120))

    stage = db.Column(db.String(40), nullable=False, default="Sourced", index=True)
    source = db.Column(db.String(80))
    rating = db.Column(db.Integer, default=3)  # 1-5 internal fit rating
    expected_comp = db.Column(db.Integer)  # annual, USD

    practice_id = db.Column(db.Integer, db.ForeignKey("practices.id"))
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)

    practice = db.relationship("Practice", back_populates="candidates")
    owner = db.relationship("User", back_populates="owned_candidates")
    notes = db.relationship(
        "Note",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="Note.created_at.desc()",
    )

    @property
    def full_name(self):
        return f"Dr. {self.first_name} {self.last_name}"

    @property
    def initials(self):
        return (self.first_name[:1] + self.last_name[:1]).upper()

    @property
    def is_active(self):
        return self.stage in ACTIVE_STAGES

    def __repr__(self):
        return f"<Candidate {self.full_name} ({self.stage})>"


class Note(db.Model):
    """A timestamped note left on a candidate by a team member."""

    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(
        db.Integer, db.ForeignKey("candidates.id"), nullable=False, index=True
    )
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    candidate = db.relationship("Candidate", back_populates="notes")
    author = db.relationship("User", back_populates="notes")

    def __repr__(self):
        return f"<Note {self.id} on candidate {self.candidate_id}>"
