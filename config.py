import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Application configuration.

    Values can be overridden with environment variables so the same code runs
    locally (SQLite) and in a shared team deployment (e.g. Postgres).
    """

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "instance", "ats.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Placeholder credentials for a future real Salesforce sync. Left blank in
    # the mock-data build; see app/salesforce.py.
    SALESFORCE_CLIENT_ID = os.environ.get("SALESFORCE_CLIENT_ID", "")
    SALESFORCE_CLIENT_SECRET = os.environ.get("SALESFORCE_CLIENT_SECRET", "")
    SALESFORCE_USERNAME = os.environ.get("SALESFORCE_USERNAME", "")
    SALESFORCE_PASSWORD = os.environ.get("SALESFORCE_PASSWORD", "")
    SALESFORCE_DOMAIN = os.environ.get("SALESFORCE_DOMAIN", "login")
