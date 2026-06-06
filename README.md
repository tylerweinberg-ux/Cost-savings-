# Oral Surgeon Recruiting ATS

A team-accessible recruiting dashboard for tracking oral surgeon candidates
through a hiring pipeline. Built with Flask + SQLite, seeded with realistic
mock data so it runs out of the box.

> Originally scoped as a "Salesforce dashboard" — the actual need is an
> applicant-tracking system. The data model mirrors a CRM shape
> (Candidate↔Contact, Practice↔Account, Note↔Task) so a real Salesforce sync
> can be added later without reworking the app. See `app/salesforce.py`.

## Features

- **Pipeline dashboard** — KPIs (total/active/hired), a conversion funnel with
  step-by-step conversion rates, a candidates-by-stage chart, and a recent
  activity feed.
- **Candidate profiles** — full profile for every doctor, editable pipeline
  stage, fit rating, owner, expected comp, and **team notes**.
- **Practices** — link candidates to specific practices; each practice page
  shows open roles and its linked/active/hired candidates.
- **Team access** — email/password login with multiple seeded team accounts
  (multi-user; everyone shares the same candidate database).
- **Search & filter** — by name/email/location, stage, practice, or active-only.

The seed data contains **200 candidates** with roughly **20 active** in the
pipeline, across 12 practices and a 4-person recruiting team.

## Quick start

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Then open http://127.0.0.1:5000 and sign in with a demo account:

| Email                      | Password   | Role        |
|----------------------------|------------|-------------|
| tyler@recruiting.example   | demo1234   | Talent Lead |
| dana@recruiting.example    | demo1234   | Recruiter   |
| marcus@recruiting.example  | demo1234   | Recruiter   |
| priya@recruiting.example   | demo1234   | Sourcer     |

The SQLite database is created and seeded automatically on first run (stored in
`instance/ats.db`).

### Reset the data

```bash
flask --app run reseed
```

## Project structure

```
app/
  __init__.py        app factory + blueprint registration
  extensions.py      shared SQLAlchemy / Flask-Login instances
  models.py          User, Practice, Candidate, Note  (+ pipeline stages)
  seed.py            deterministic mock-data generator
  salesforce.py      stub sync layer for a future live Salesforce org
  routes/            auth, dashboard, candidates, practices blueprints
  templates/         Jinja2 templates
  static/css/        styling
config.py            configuration (env-var overridable)
run.py               dev entry point
```

## Connecting real Salesforce later

1. Create a Salesforce Connected App and grab the client id/secret.
2. Set `SALESFORCE_*` environment variables (see `config.py`).
3. `pip install simple-salesforce` and implement `pull_candidates()` /
   `push_candidate()` in `app/salesforce.py`. The object mapping is documented
   there. The rest of the app already reads/writes through the local models, so
   no UI changes are needed.

## Deploying for the team

For shared access, run behind a WSGI server (e.g. gunicorn) and point
`DATABASE_URL` at a shared database (e.g. Postgres) instead of SQLite:

```bash
pip install gunicorn
export SECRET_KEY="<random-secret>"
export DATABASE_URL="postgresql://user:pass@host/dbname"
gunicorn "app:create_app()" -b 0.0.0.0:8000
```
