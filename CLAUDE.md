# CLAUDE.md — Cost Savings Repository

This file provides context and conventions for AI assistants (Claude, Copilot, etc.) working in this repository.

## Repository Overview

**Name:** Cost-savings-
**Owner:** tylerweinberg-ux
**Purpose:** A Python tool that fetches personal Whoop fitness data and sends it to Claude for workout analysis and coaching insights.

## Repository Structure

```
Cost-savings-/
├── whoop_claude.py      # Main script — Whoop API client + Claude analysis
├── requirements.txt     # Python dependencies
├── .env.example         # Template for required environment variables
├── .gitignore           # Excludes .env, tokens file, and bytecode
└── CLAUDE.md            # This file — AI assistant context and conventions
```

**Key files:**
- `whoop_claude.py` — Single-file app. Contains OAuth2 flow, `WhoopClient` class, data formatters, and Claude streaming analysis.
- `.whoop_tokens.json` — Auto-created at runtime; stores OAuth tokens. Never committed (in `.gitignore`).
- `.env` — Created by user from `.env.example`; never committed.

## Tech Stack

- **Language:** Python 3.10+
- **AI:** Anthropic SDK (`anthropic`) — uses `claude-opus-4-6` with adaptive thinking and streaming
- **External API:** Whoop Developer API (OAuth 2.0 authorization code flow)
- **HTTP:** `requests`
- **Config:** `python-dotenv`

## Development Setup

```bash
# Clone the repository
git clone <repo-url>
cd Cost-savings-

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your Whoop client credentials and Anthropic API key

# Run — first run opens browser for Whoop OAuth
python whoop_claude.py

# Options
python whoop_claude.py --days 14   # Analyze last 14 days
python whoop_claude.py --auth      # Force re-authentication
```

## Whoop API Setup

1. Register a developer app at the Whoop developer portal
2. Set the redirect URI to `http://localhost:8888/callback`
3. Request scopes: `read:workout read:recovery read:sleep read:profile offline`
4. Copy the client ID and secret into `.env`

## Environment Variables

All required. Copy `.env.example` to `.env` and fill in values.

```
WHOOP_CLIENT_ID=        # From Whoop developer app
WHOOP_CLIENT_SECRET=    # From Whoop developer app
ANTHROPIC_API_KEY=      # From console.anthropic.com
```

Never commit `.env` or `.whoop_tokens.json`. Both are in `.gitignore`.

## Architecture Notes

- **OAuth flow:** `authenticate()` starts a local HTTP server on port 8888, opens the browser to Whoop's auth URL, catches the callback code, and exchanges it for tokens. Tokens are saved to `.whoop_tokens.json` and refreshed automatically on subsequent runs.
- **Pagination:** `WhoopClient._paginate()` handles Whoop's cursor-based pagination for workouts and recoveries.
- **Data formatting:** `format_workouts()` and `format_recoveries()` convert raw API JSON into human-readable text passed as context to Claude.
- **Claude call:** Uses `client.messages.stream()` with `thinking: {"type": "adaptive"}` and `claude-opus-4-6`. Streams output directly to stdout. Token usage is printed after the response.

## Key Metrics Tracked

**Workouts:** Strain score, sport type, duration, average HR, max HR, calories, HR zone breakdown (Z1–Z6)

**Recovery:** Recovery score (%), HRV (RMSSD ms), resting heart rate, sleep performance %, SpO2 %

## Branch Conventions

| Branch Pattern | Purpose |
|---|---|
| `master` / `main` | Stable, production-ready code |
| `claude/<description>-<session-id>` | AI-assisted development branches |
| `feature/<short-description>` | New features |
| `fix/<short-description>` | Bug fixes |

## Git Workflow

1. **Never commit directly to `main` or `master`** without a review.
2. All changes should be made on a feature or AI-specific branch.
3. When work is complete, open a pull request targeting `main`.
4. AI assistant branches must be named `claude/<description>-<session-id>`.
5. Use clear, descriptive commit messages in the imperative mood.

## Code Conventions

- **Language:** Python, `snake_case` for variables/functions, `PascalCase` for classes.
- **Clarity over cleverness:** Prefer readable, self-documenting code.
- **Small, focused functions:** Each function does one thing.
- **No dead code:** Remove unused variables, imports, and functions.
- **Comments:** Only where logic is non-obvious.
- **Error handling:** Validate at system boundaries (API calls, CLI input). Raise or `sys.exit()` with a clear message on failure.

## AI Assistant Guidelines

When working in this repository, AI assistants should:

1. **Read before modifying.** Always read existing files before editing them.
2. **Avoid over-engineering.** Make only the changes requested or clearly necessary.
3. **Keep it a single file.** Unless the feature clearly warrants splitting, keep logic in `whoop_claude.py`.
4. **No backwards-compatibility hacks.** Delete unused code rather than wrapping it.
5. **Update this file.** When the tech stack, structure, or workflows change, update the relevant sections in `CLAUDE.md`.
6. **Commit and push to the correct branch.** Never push to `main`/`master` directly.
7. **No speculative features.** Do not add functionality that isn't requested.
8. **Never log or print tokens/secrets.** The `.whoop_tokens.json` file is write-only from user perspective.

## Testing

No automated tests are configured yet. Manual testing:

```bash
# Test authentication flow
python whoop_claude.py --auth

# Test with minimal data window
python whoop_claude.py --days 1
```

If tests are added, use `pytest` and place test files in `tests/`.

## Updating This File

Update `CLAUDE.md` whenever:
- New features or CLI flags are added to `whoop_claude.py`
- New environment variables are required
- The architecture changes significantly
- New dependencies are added to `requirements.txt`
