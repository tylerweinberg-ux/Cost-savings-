"""Salesforce sync layer (stub).

This build runs on seeded mock data. When you're ready to connect a real
Salesforce org, fill in the credentials in config.py (via environment
variables) and implement the two functions below using `simple-salesforce`:

    pip install simple-salesforce

Object mapping used by this app:
    Candidate  <-> Contact   (or Lead, depending on your SF setup)
    Practice   <-> Account
    Note       <-> Task / ContentNote

The functions are written so the rest of the app never needs to change when
you switch from mock data to a live org.
"""
from flask import current_app


def is_configured():
    """True when Salesforce credentials are present in config."""
    cfg = current_app.config
    return bool(cfg.get("SALESFORCE_CLIENT_ID") and cfg.get("SALESFORCE_USERNAME"))


def _client():  # pragma: no cover - requires live credentials
    """Build an authenticated Salesforce client.

    Example implementation (uncomment after installing simple-salesforce):

        from simple_salesforce import Salesforce
        cfg = current_app.config
        return Salesforce(
            username=cfg["SALESFORCE_USERNAME"],
            password=cfg["SALESFORCE_PASSWORD"],
            consumer_key=cfg["SALESFORCE_CLIENT_ID"],
            consumer_secret=cfg["SALESFORCE_CLIENT_SECRET"],
            domain=cfg["SALESFORCE_DOMAIN"],
        )
    """
    raise NotImplementedError(
        "Live Salesforce sync is not configured. Set SALESFORCE_* env vars and "
        "implement app/salesforce.py._client()."
    )


def pull_candidates():  # pragma: no cover - requires live credentials
    """Pull contacts/leads from Salesforce and upsert into the local DB.

    Map SF fields -> Candidate columns, then commit. Returns the number of
    records synced.
    """
    raise NotImplementedError("Implement pull_candidates() for live sync.")


def push_candidate(candidate):  # pragma: no cover - requires live credentials
    """Push a single candidate's stage/notes back to Salesforce."""
    raise NotImplementedError("Implement push_candidate() for live sync.")
