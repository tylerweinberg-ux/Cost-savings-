"""Seed the database with realistic mock recruiting data.

Generates ~200 oral surgeon candidates, ~20 of whom are actively in process,
across a set of practices and a small recruiting team. Deterministic (fixed
RNG seed) so the dashboard numbers are stable between runs.
"""
import random
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Candidate, Note, Practice, STAGES, User

RNG = random.Random(42)

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "David", "Elizabeth", "William", "Barbara", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Christopher", "Karen", "Daniel",
    "Nancy", "Matthew", "Lisa", "Anthony", "Margaret", "Mark", "Sandra",
    "Donald", "Ashley", "Steven", "Kimberly", "Paul", "Emily", "Andrew",
    "Donna", "Joshua", "Michelle", "Kenneth", "Carol", "Kevin", "Amanda",
    "Brian", "Melissa", "George", "Deborah", "Timothy", "Stephanie", "Ronald",
    "Rebecca", "Priya", "Wei", "Carlos", "Aisha", "Diego", "Mei", "Omar",
    "Sofia", "Raj", "Yuki", "Hassan", "Ingrid", "Mateo", "Fatima", "Kenji",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Patel", "Campbell", "Mitchell",
    "Carter", "Roberts", "Chen", "Kim", "Singh", "Okafor", "Cohen", "Reyes",
]

DENTAL_SCHOOLS = [
    "Harvard School of Dental Medicine",
    "University of Michigan School of Dentistry",
    "UCSF School of Dentistry",
    "University of Pennsylvania (Penn Dental)",
    "Columbia College of Dental Medicine",
    "University of North Carolina (Adams)",
    "University of Washington School of Dentistry",
    "Ohio State University College of Dentistry",
    "NYU College of Dentistry",
    "University of Texas (UTHealth) School of Dentistry",
]

SOURCES = [
    "LinkedIn", "Referral", "AAOMS Conference", "Residency Program",
    "Direct Outreach", "Job Board", "Recruiter Network",
]

NOTE_SNIPPETS = [
    "Initial call went well. Strong communicator, open to relocation.",
    "Currently in residency, available after June. Wants to discuss comp.",
    "Excellent surgical volume in residency. Interested in partnership track.",
    "Prefers a group practice over solo. Flagging for the metro practices.",
    "Reference check came back glowing from program director.",
    "Asked for a follow-up with the clinical director before the on-site.",
    "Comp expectations are a bit above band — revisit with practice.",
    "Great culture fit on the panel interview. Team is enthusiastic.",
    "Negotiating start date; needs to wrap up current contract.",
    "Slow to respond lately — sending a check-in email this week.",
    "Declined our offer, accepted a competing one closer to family.",
    "Re-engaging after 6 months. Their situation has changed.",
]

PRACTICES = [
    ("Summit Oral & Maxillofacial Surgery", "Denver", "CO", "West"),
    ("Bayview Surgical Dental Group", "San Diego", "CA", "West"),
    ("Lakeshore OMS Associates", "Chicago", "IL", "Midwest"),
    ("Piedmont Facial Surgery Center", "Atlanta", "GA", "Southeast"),
    ("Harborline Oral Surgery", "Boston", "MA", "Northeast"),
    ("Desert Ridge Oral Surgery", "Phoenix", "AZ", "West"),
    ("Riverside Maxillofacial Institute", "Austin", "TX", "South"),
    ("Cascade Oral & Implant Surgery", "Seattle", "WA", "West"),
    ("Greater Triangle OMS", "Raleigh", "NC", "Southeast"),
    ("Metro Manhattan Oral Surgery", "New York", "NY", "Northeast"),
    ("Bluegrass Surgical Arts", "Louisville", "KY", "South"),
    ("Twin Cities Facial & Oral Surgery", "Minneapolis", "MN", "Midwest"),
]

TEAM = [
    ("Tyler Weinberg", "tyler@recruiting.example", "Talent Lead", "demo1234"),
    ("Dana Whitfield", "dana@recruiting.example", "Recruiter", "demo1234"),
    ("Marcus Reed", "marcus@recruiting.example", "Recruiter", "demo1234"),
    ("Priya Nair", "priya@recruiting.example", "Sourcer", "demo1234"),
]

# Target counts across the 200-candidate pipeline. Tuned so ~20 land in the
# active stages (Contacted/Screening/Interview/Offer).
STAGE_TARGETS = {
    "Sourced": 96,
    "Contacted": 8,
    "Screening": 6,
    "Interview": 4,
    "Offer": 2,
    "Hired": 14,
    "Passed": 70,
}
TOTAL_CANDIDATES = sum(STAGE_TARGETS.values())  # 200


def _build_stage_list():
    stages = []
    for stage, count in STAGE_TARGETS.items():
        stages.extend([stage] * count)
    RNG.shuffle(stages)
    return stages


def seed_if_empty():
    """Seed only when the database has no candidates yet."""
    if db.session.query(Candidate.id).first() is not None:
        return
    _seed()


def reseed():
    """Wipe all rows and reseed from scratch."""
    Note.query.delete()
    Candidate.query.delete()
    Practice.query.delete()
    User.query.delete()
    db.session.commit()
    _seed()


def _seed():
    now = datetime.utcnow()

    users = []
    for name, email, role, password in TEAM:
        u = User(name=name, email=email, role=role)
        u.set_password(password)
        db.session.add(u)
        users.append(u)

    practices = []
    for name, city, state, region in PRACTICES:
        p = Practice(
            name=name,
            city=city,
            state=state,
            region=region,
            num_providers=RNG.randint(2, 9),
            open_roles=RNG.randint(1, 3),
            notes=f"{region} region. Actively interviewing for oral surgeon coverage.",
        )
        db.session.add(p)
        practices.append(p)

    db.session.flush()  # assign ids

    stages = _build_stage_list()
    used_names = set()

    for i in range(TOTAL_CANDIDATES):
        # Unique-ish names.
        while True:
            first = RNG.choice(FIRST_NAMES)
            last = RNG.choice(LAST_NAMES)
            if (first, last) not in used_names:
                used_names.add((first, last))
                break

        stage = stages[i]
        grad_year = RNG.randint(2005, 2024)
        years_exp = max(0, 2025 - grad_year - RNG.randint(0, 2))

        # Candidates that have advanced past sourcing get a practice + owner.
        has_engagement = stage != "Sourced"
        practice = RNG.choice(practices) if has_engagement and RNG.random() < 0.85 else None
        owner = RNG.choice(users) if has_engagement else RNG.choice(users[:3])

        created = now - timedelta(days=RNG.randint(5, 420))
        last_activity = created + timedelta(days=RNG.randint(0, 30))
        if last_activity > now:
            last_activity = now

        c = Candidate(
            first_name=first,
            last_name=last,
            email=f"{first.lower()}.{last.lower()}@example.com",
            phone=f"({RNG.randint(200, 989)}) {RNG.randint(200, 989)}-{RNG.randint(1000, 9999)}",
            dental_school=RNG.choice(DENTAL_SCHOOLS),
            grad_year=grad_year,
            years_experience=years_exp,
            current_location=f"{RNG.choice(PRACTICES)[1]}, {RNG.choice(PRACTICES)[2]}",
            stage=stage,
            source=RNG.choice(SOURCES),
            rating=RNG.randint(2, 5),
            expected_comp=RNG.randint(38, 65) * 10000,
            practice=practice,
            owner=owner,
            created_at=created,
            last_activity=last_activity,
        )
        db.session.add(c)
        db.session.flush()

        # Add 0-3 notes for engaged candidates.
        if has_engagement:
            for _ in range(RNG.randint(1, 3)):
                note_time = created + timedelta(days=RNG.randint(0, 25))
                if note_time > now:
                    note_time = now
                db.session.add(
                    Note(
                        candidate_id=c.id,
                        author_id=RNG.choice(users).id,
                        body=RNG.choice(NOTE_SNIPPETS),
                        created_at=note_time,
                    )
                )

    db.session.commit()
