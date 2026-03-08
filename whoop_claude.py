#!/usr/bin/env python3
"""
Whoop → Claude Workout Analyzer

Fetches your recent Whoop workout data and key metrics,
then sends them to Claude for intelligent analysis and insights.

Usage:
    python whoop_claude.py              # Analyze last 7 days
    python whoop_claude.py --days 14   # Analyze last 14 days
    python whoop_claude.py --auth      # Re-authenticate with Whoop
"""

import argparse
import json
import os
import sys
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import anthropic
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
WHOOP_CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
WHOOP_CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_API_BASE = "https://api.prod.whoop.com/developer/v1"

REDIRECT_URI = "http://localhost:8888/callback"
SCOPES = "read:workout read:recovery read:sleep read:profile offline"
TOKEN_FILE = Path(".whoop_tokens.json")

# ── Sport ID → Name mapping ────────────────────────────────────────────────────
SPORT_MAP = {
    -1: "Activity", 0: "Running", 1: "Cycling", 16: "Baseball",
    17: "Basketball", 18: "Rowing", 19: "Fencing", 20: "Field Hockey",
    21: "Football", 22: "Golf", 24: "Ice Hockey", 25: "Lacrosse",
    27: "Rugby", 28: "Sailing", 29: "Skiing", 30: "Soccer",
    31: "Softball", 32: "Squash", 33: "Swimming", 34: "Tennis",
    35: "Track & Field", 36: "Volleyball", 37: "Water Polo", 38: "Wrestling",
    39: "Boxing", 42: "Dance", 43: "Pilates", 44: "Yoga",
    45: "Weightlifting", 47: "Cross Country Skiing", 48: "Functional Fitness",
    49: "Duathlon", 51: "Gymnastics", 52: "Hiking/Rucking", 53: "Horseback Riding",
    55: "Kayaking", 56: "Martial Arts", 57: "Mountain Biking", 59: "Powerlifting",
    60: "Rock Climbing", 61: "Paddleboarding", 62: "Triathlon", 63: "Walking",
    64: "Surfing", 65: "Elliptical", 66: "Stairmaster", 70: "Meditation",
    71: "Other", 82: "Obstacle Course Racing", 83: "Motor Racing", 84: "HIIT",
    85: "Spin", 86: "Jiu Jitsu", 87: "Manual Labor", 88: "Cricket",
    89: "Pickleball", 90: "Inline Skating", 91: "Box Fitness", 99: "Commuting",
    100: "Gaming", 101: "Snowboarding",
}


# ── OAuth 2.0 Authentication ───────────────────────────────────────────────────

def save_tokens(tokens: dict):
    TOKEN_FILE.write_text(json.dumps(tokens))


def load_tokens() -> dict | None:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None


def refresh_access_token(refresh_token: str) -> dict:
    resp = requests.post(WHOOP_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": WHOOP_CLIENT_ID,
        "client_secret": WHOOP_CLIENT_SECRET,
    })
    resp.raise_for_status()
    tokens = resp.json()
    save_tokens(tokens)
    return tokens


def authenticate() -> str:
    """Run OAuth2 authorization code flow; return access token."""
    auth_code_holder = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            if "code" in params:
                auth_code_holder["code"] = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"<h2>Authentication successful. You can close this tab.</h2>"
            )

        def log_message(self, *_):
            pass  # Suppress request logs

    server = HTTPServer(("localhost", 8888), CallbackHandler)
    server.timeout = 120

    auth_params = urlencode({
        "response_type": "code",
        "client_id": WHOOP_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
    })
    auth_url = f"{WHOOP_AUTH_URL}?{auth_params}"

    print("Opening Whoop authorization page in your browser...")
    webbrowser.open(auth_url)
    server.handle_request()

    code = auth_code_holder.get("code")
    if not code:
        raise RuntimeError("Authorization failed — no code received.")

    resp = requests.post(WHOOP_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": WHOOP_CLIENT_ID,
        "client_secret": WHOOP_CLIENT_SECRET,
    })
    resp.raise_for_status()
    tokens = resp.json()
    save_tokens(tokens)
    print("Authenticated successfully.\n")
    return tokens["access_token"]


def get_access_token() -> str:
    """Return a valid access token, refreshing if possible, else re-auth."""
    tokens = load_tokens()
    if tokens:
        try:
            tokens = refresh_access_token(tokens["refresh_token"])
            return tokens["access_token"]
        except Exception:
            pass  # Fall through to full re-auth
    return authenticate()


# ── Whoop API Client ───────────────────────────────────────────────────────────

class WhoopClient:
    def __init__(self, access_token: str):
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {access_token}"

    def _get(self, path: str, params: dict = None) -> dict:
        resp = self.session.get(f"{WHOOP_API_BASE}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _paginate(self, path: str, start: datetime, end: datetime) -> list[dict]:
        results = []
        params = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "limit": 25,
        }
        while True:
            data = self._get(path, params)
            results.extend(data.get("records", []))
            next_token = data.get("next_token")
            if not next_token:
                break
            params["nextToken"] = next_token
        return results

    def get_workouts(self, start: datetime, end: datetime) -> list[dict]:
        return self._paginate("/activity/workout", start, end)

    def get_recoveries(self, start: datetime, end: datetime) -> list[dict]:
        return self._paginate("/recovery", start, end)

    def get_profile(self) -> dict:
        return self._get("/user/profile/basic")


# ── Data Formatting ────────────────────────────────────────────────────────────

def format_duration(seconds: int) -> str:
    mins = seconds // 60
    return f"{mins // 60}h {mins % 60}m" if mins >= 60 else f"{mins}m"


def kj_to_kcal(kj: float) -> int:
    return round(kj / 4.184)


def format_workouts(workouts: list[dict]) -> str:
    if not workouts:
        return "No workouts recorded in this period."

    lines = []
    for w in sorted(workouts, key=lambda x: x["start"]):
        score = w.get("score") or {}
        sport = SPORT_MAP.get(w.get("sport_id", -1), "Activity")
        start_dt = datetime.fromisoformat(w["start"].replace("Z", "+00:00"))

        strain = score.get("strain", "N/A")
        avg_hr = score.get("average_heart_rate", "N/A")
        max_hr = score.get("max_heart_rate", "N/A")
        kj = score.get("kilojoule", 0)
        calories = kj_to_kcal(kj) if kj else "N/A"
        duration_s = score.get("duration", 0)

        lines.append(
            f"  [{start_dt.strftime('%b %d, %I:%M %p')}] {sport}\n"
            f"    Strain: {strain}  |  Duration: {format_duration(duration_s)}  "
            f"|  Calories: {calories} kcal\n"
            f"    Heart Rate: avg {avg_hr} bpm, max {max_hr} bpm"
        )

        zone_data = score.get("zone_duration", {})
        if zone_data:
            zone_labels = [
                ("Z1 (<50%)", "zone_zero_milli"),
                ("Z2 (50-60%)", "zone_one_milli"),
                ("Z3 (60-70%)", "zone_two_milli"),
                ("Z4 (70-80%)", "zone_three_milli"),
                ("Z5 (80-90%)", "zone_four_milli"),
                ("Z6 (90-100%)", "zone_five_milli"),
            ]
            zone_parts = [
                f"{label}: {zone_data[key] // 60000}m"
                for label, key in zone_labels
                if zone_data.get(key, 0) > 0
            ]
            if zone_parts:
                lines.append(f"    HR Zones: {', '.join(zone_parts)}")

    return "\n".join(lines)


def format_recoveries(recoveries: list[dict]) -> str:
    if not recoveries:
        return "No recovery data available for this period."

    lines = []
    for r in sorted(recoveries, key=lambda x: x.get("created_at", "")):
        score = r.get("score") or {}
        created_str = r.get("created_at", "")
        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))

        recovery_score = score.get("recovery_score", "N/A")
        hrv_raw = score.get("hrv_rmssd_milli", "N/A")
        hrv = round(hrv_raw, 1) if isinstance(hrv_raw, (int, float)) else hrv_raw
        rhr = score.get("resting_heart_rate", "N/A")
        sleep_perf = score.get("sleep_performance_percentage", "N/A")
        spo2 = score.get("spo2_percentage", "N/A")

        lines.append(
            f"  [{created.strftime('%b %d')}] Recovery: {recovery_score}%  |  "
            f"HRV: {hrv} ms  |  RHR: {rhr} bpm  |  "
            f"Sleep Performance: {sleep_perf}%  |  SpO2: {spo2}%"
        )
    return "\n".join(lines)


# ── Claude Analysis ────────────────────────────────────────────────────────────

def analyze_with_claude(
    profile: dict,
    workouts: list[dict],
    recoveries: list[dict],
    days: int,
):
    name = profile.get("first_name", "Athlete")
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    workout_text = format_workouts(workouts)
    recovery_text = format_recoveries(recoveries)

    prompt = f"""You are a performance coach analyzing Whoop biometric data. Today is {today}.

Athlete: {name}
Analysis window: Last {days} days
Total workouts: {len(workouts)}

── WORKOUT DATA ──────────────────────────────────────────
{workout_text}

── RECOVERY & HRV DATA ───────────────────────────────────
{recovery_text}

Please provide a concise, actionable analysis covering:
1. **Workout Summary** — Volume, intensity patterns, and sport breakdown
2. **Recovery Trends** — HRV trajectory, resting HR, and recovery score patterns
3. **Strain vs Recovery Balance** — Is the athlete overreaching, well-balanced, or undertraining?
4. **Key Observations** — Notable patterns, high-strain days with poor recovery, or positive trends
5. **Recommendations** — 2–3 specific, actionable suggestions based on this data

Be direct and coach-like. Focus on patterns and what to do next, not raw data recitation."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print(f"\n{'=' * 60}")
    print(f"  WHOOP ANALYSIS — Last {days} Days  ({name})")
    print(f"{'=' * 60}\n")

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=1500,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)

    final = stream.get_final_message()
    usage = final.usage
    print(f"\n\n{'=' * 60}")
    print(f"  Tokens used: {usage.input_tokens} in / {usage.output_tokens} out")
    print(f"{'=' * 60}")


# ── CLI Entry Point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Analyze your Whoop workout data with Claude"
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="Number of past days to analyze (default: 7)"
    )
    parser.add_argument(
        "--auth", action="store_true",
        help="Re-authenticate with Whoop (clears stored tokens)"
    )
    args = parser.parse_args()

    missing = [
        v for v in ("WHOOP_CLIENT_ID", "WHOOP_CLIENT_SECRET", "ANTHROPIC_API_KEY")
        if not os.getenv(v)
    ]
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)

    if args.auth and TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print("Cleared stored tokens. Re-authenticating...\n")

    print("Connecting to Whoop...")
    access_token = get_access_token()
    client = WhoopClient(access_token)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)

    print(f"Fetching data for the last {args.days} days...")
    try:
        profile = client.get_profile()
        workouts = client.get_workouts(start, end)
        recoveries = client.get_recoveries(start, end)
    except requests.HTTPError as e:
        print(f"Error fetching Whoop data: {e}")
        sys.exit(1)

    print(f"Found {len(workouts)} workouts. Analyzing with Claude...")
    analyze_with_claude(profile, workouts, recoveries, args.days)


if __name__ == "__main__":
    main()
