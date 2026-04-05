#!/usr/bin/env python3
"""
Granola Weekly Call Summary
============================
Fetches all meetings from Granola AI over the past week, uses Claude to extract
key takeaways and action items from each, and emails you a digest.

Requirements:
    pip install -r requirements.txt

Setup:
    Copy .env.example to .env and fill in your credentials.

Run manually:
    python weekly_summary.py

Run as a weekly cron job (every Monday at 8am):
    0 8 * * 1 cd /path/to/this/dir && python weekly_summary.py >> /tmp/granola_summary.log 2>&1

Dry run (preview without sending email):
    DRY_RUN=1 python weekly_summary.py
"""

import os
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import anthropic
import requests
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
GRANOLA_API_KEY = os.environ["GRANOLA_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME") or EMAIL_FROM
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
DAYS_BACK = int(os.environ.get("DAYS_BACK", "7"))
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes")

GRANOLA_BASE_URL = "https://public-api.granola.ai"
GRANOLA_RATE_LIMIT_DELAY = 0.25  # 4 req/sec to stay under 5/sec limit


# --- Granola API ---

def _granola_headers() -> dict:
    return {"Authorization": f"Bearer {GRANOLA_API_KEY}"}


def fetch_notes_from_past_week() -> list[dict]:
    """Fetch all Granola notes created in the past DAYS_BACK days (paginated)."""
    since = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    notes = []
    cursor = None

    while True:
        params: dict = {"created_after": since_iso}
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(
            f"{GRANOLA_BASE_URL}/v1/notes",
            headers=_granola_headers(),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        notes.extend(data.get("notes", []))

        if not data.get("hasMore"):
            break
        cursor = data.get("cursor")
        time.sleep(GRANOLA_RATE_LIMIT_DELAY)

    return notes


def fetch_note_details(note_id: str) -> dict:
    """Fetch a single note including its AI summary and transcript."""
    resp = requests.get(
        f"{GRANOLA_BASE_URL}/v1/notes/{note_id}",
        headers=_granola_headers(),
        params={"include": "transcript"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# --- Claude Analysis ---

def extract_takeaways_and_todos(note: dict) -> str:
    """
    Use Claude to extract key takeaways and action items from a meeting note.
    Returns formatted text with KEY TAKEAWAYS and ACTION ITEMS sections.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    title = note.get("title", "Untitled Meeting")
    summary = note.get("summary", "")
    # Transcript can be very long — cap it to keep costs reasonable
    raw_transcript = note.get("transcript", "")
    if isinstance(raw_transcript, list):
        # Granola returns transcript as list of segments with text/timestamp
        transcript = " ".join(
            seg.get("text", "") for seg in raw_transcript if isinstance(seg, dict)
        )
    else:
        transcript = str(raw_transcript)
    transcript = transcript[:6000]  # ~1500 tokens

    meeting_content = f"Meeting Title: {title}\n\n"
    if summary:
        meeting_content += f"AI Summary:\n{summary}\n\n"
    if transcript:
        meeting_content += f"Transcript (excerpt):\n{transcript}\n\n"

    if not summary and not transcript:
        return "(No content available for this meeting)"

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=800,
        thinking={"type": "adaptive"},
        messages=[
            {
                "role": "user",
                "content": (
                    "You are a sharp executive assistant. Analyze this meeting and extract:\n\n"
                    "1. KEY TAKEAWAYS — 3 to 5 bullet points covering the most important "
                    "insights, decisions, and outcomes from the meeting.\n"
                    "2. ACTION ITEMS — specific tasks, follow-ups, or commitments made. "
                    "Include the responsible person if mentioned. If none, write 'None identified.'\n\n"
                    "Be concise and specific. No filler words.\n\n"
                    "Format exactly as:\n\n"
                    "KEY TAKEAWAYS:\n"
                    "• ...\n\n"
                    "ACTION ITEMS:\n"
                    "• ...\n\n"
                    f"---\n{meeting_content}"
                ),
            }
        ],
    )

    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    return "(Analysis unavailable)"


# --- Email ---

def _strip_leading_zero(s: str) -> str:
    """Remove leading zeros from day/hour numbers for cleaner date display."""
    return s.replace(" 0", " ").replace(":0", ":0")  # keep :00 but fix " 01" → " 1"


def _format_meeting_date(meeting_date: str) -> str:
    if not meeting_date:
        return ""
    try:
        dt = datetime.fromisoformat(meeting_date.replace("Z", "+00:00"))
        return _strip_leading_zero(dt.strftime("%A, %b %d at %I:%M %p"))
    except ValueError:
        return meeting_date


def build_email_html(week_start: datetime, week_end: datetime, processed_notes: list[dict]) -> str:
    """Build a clean HTML email with all meeting summaries."""
    week_range = (
        f"{_strip_leading_zero(week_start.strftime('%b %d'))} – "
        f"{_strip_leading_zero(week_end.strftime('%b %d, %Y'))}"
    )
    count = len(processed_notes)

    meetings_html = ""
    if not processed_notes:
        meetings_html = (
            '<p style="color:#666;font-style:italic;padding:20px 0;">'
            "No meetings recorded this week — enjoy the quiet! 🎉</p>"
        )
    else:
        for note in processed_notes:
            title = note.get("title", "Untitled Meeting")
            date_str = _format_meeting_date(note.get("meeting_date", ""))
            analysis = note.get("analysis", "").replace("\n", "<br>")

            # Color bullet points
            analysis = analysis.replace(
                "KEY TAKEAWAYS:",
                '<strong style="color:#2c5282">📌 KEY TAKEAWAYS:</strong>',
            ).replace(
                "ACTION ITEMS:",
                '<strong style="color:#276749">✅ ACTION ITEMS:</strong>',
            )

            date_html = (
                f'<p style="color:#718096;font-size:13px;margin:4px 0 12px">📅 {date_str}</p>'
                if date_str
                else ""
            )

            meetings_html += f"""
<div style="background:#f7fafc;border-left:4px solid #4299e1;padding:16px 20px;
            margin:20px 0;border-radius:0 8px 8px 0;">
  <h3 style="margin:0 0 4px;color:#1a202c;font-size:17px">🎙️ {title}</h3>
  {date_html}
  <div style="font-size:14px;line-height:1.7;color:#2d3748">{analysis}</div>
</div>
"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
             color:#2d3748;max-width:680px;margin:0 auto;padding:24px;background:#fff">

  <div style="background:linear-gradient(135deg,#2c5282,#4299e1);
              padding:24px 28px;border-radius:12px;margin-bottom:24px">
    <h1 style="color:#fff;margin:0 0 6px;font-size:22px">📋 Weekly Call Summary</h1>
    <p style="color:#bee3f8;margin:0;font-size:14px">
      {week_range} &nbsp;·&nbsp;
      <strong>{count} meeting{"s" if count != 1 else ""}</strong>
    </p>
  </div>

  {meetings_html}

  <div style="margin-top:36px;padding-top:16px;border-top:1px solid #e2e8f0;
              color:#a0aec0;font-size:12px;text-align:center">
    Generated by Granola Weekly Summary &nbsp;·&nbsp; Powered by Claude AI<br>
    To change frequency or recipients, edit your <code>.env</code> file.
  </div>

</body>
</html>"""


def send_email(subject: str, html_content: str) -> None:
    """Send an HTML email via SMTP with STARTTLS."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

    print(f"✅ Email sent to {EMAIL_TO}")


# --- Main ---

def main() -> None:
    print(f"🔍 Fetching Granola notes from the past {DAYS_BACK} days...")

    try:
        notes = fetch_notes_from_past_week()
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            raise SystemExit(
                "❌ Granola authentication failed. Check your GRANOLA_API_KEY "
                "(must start with 'grn_' and require Business/Enterprise plan)."
            ) from e
        raise

    print(f"📝 Found {len(notes)} meeting(s)")

    processed_notes = []
    for i, note in enumerate(notes, 1):
        note_id = note.get("id", "")
        title = note.get("title", "Untitled")
        print(f"  [{i}/{len(notes)}] Analyzing: {title}")

        try:
            full_note = fetch_note_details(note_id)
            time.sleep(GRANOLA_RATE_LIMIT_DELAY)

            analysis = extract_takeaways_and_todos(full_note)
            processed_notes.append({**full_note, "analysis": analysis})

        except requests.HTTPError as e:
            print(f"  ⚠️  Skipped (HTTP {e.response.status_code}): {title}")
        except Exception as e:
            print(f"  ⚠️  Skipped ({type(e).__name__}): {title} — {e}")

    week_end = datetime.now(timezone.utc)
    week_start = week_end - timedelta(days=DAYS_BACK)

    html = build_email_html(week_start, week_end, processed_notes)
    subject = (
        f"📋 Weekly Call Summary — "
        f"{_strip_leading_zero(week_start.strftime('%b %d'))} to "
        f"{_strip_leading_zero(week_end.strftime('%b %d, %Y'))} "
        f"({len(processed_notes)} meeting{'s' if len(processed_notes) != 1 else ''})"
    )

    if DRY_RUN:
        print("\n" + "=" * 60)
        print("DRY RUN — preview (email not sent)")
        print("=" * 60)
        print(f"Subject: {subject}\n")
        for note in processed_notes:
            print(f"\n{'─' * 50}")
            print(f"Meeting: {note.get('title', 'Untitled')}")
            date_str = _format_meeting_date(note.get("meeting_date", ""))
            if date_str:
                print(f"Date:    {date_str}")
            print(f"{'─' * 50}")
            print(note.get("analysis", ""))
        print("\n" + "=" * 60)
        print("Set DRY_RUN=false (or unset it) to send the real email.")
    else:
        print(f"\n📧 Sending weekly summary email...")
        send_email(subject, html)


if __name__ == "__main__":
    main()
