# Weekly Brief

A TypeScript cron job that fetches your Microsoft 365 calendar events and
unread emails, summarises them with Claude, and emails you a weekly brief.

Runs on [Railway](https://railway.app) on a cron schedule.

---

## Azure App Registration (one-time setup)

1. Go to [portal.azure.com](https://portal.azure.com) → **Azure Active Directory** → **App registrations** → **New registration**.
2. **Name:** `Aviva Weekly Brief`
3. **Supported account types:** _Accounts in any organizational directory and personal Microsoft accounts_
4. **Redirect URI:** `Web` → `http://localhost:3000/callback`
5. Click **Register**.
6. From the app overview page:
   - Copy **Application (client) ID** → `MICROSOFT_CLIENT_ID`
   - Copy **Directory (tenant) ID** → `MICROSOFT_TENANT_ID`
7. Go to **Certificates & secrets** → **New client secret** → copy the **Value** → `MICROSOFT_CLIENT_SECRET`
8. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions** → add:
   - `Calendars.Read`
   - `Mail.Read`
9. Click **Grant admin consent** (or have your tenant admin do so).

---

## Getting the Initial Refresh Token

This is a one-time step you run locally.

```bash
# 1. Install dependencies
npm install

# 2. Copy the env template and fill in the three Azure values from above
cp .env.example .env
# edit .env: set MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_TENANT_ID

# 3. Run the token helper
npm run get-token
# A browser window opens. Sign in and consent.
# The terminal prints: MICROSOFT_REFRESH_TOKEN=...

# 4. Copy that value into your Railway environment variables.
```

You will not need to repeat this step unless you revoke access to the app or
it has been idle for more than 90 days (the weekly cron prevents that).

---

## Environment Variables

| Variable | Description |
|---|---|
| `MICROSOFT_CLIENT_ID` | Azure app registration client ID |
| `MICROSOFT_CLIENT_SECRET` | Azure app registration client secret |
| `MICROSOFT_TENANT_ID` | Tenant ID, or `common` for personal accounts |
| `MICROSOFT_REFRESH_TOKEN` | Obtained via `npm run get-token` |
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port (default `587`) |
| `SMTP_SECURE` | `true` for port 465 TLS, otherwise `false` |
| `SMTP_USER` | SMTP username |
| `SMTP_PASS` | SMTP password |
| `BRIEF_FROM_EMAIL` | Sender address for the brief |
| `BRIEF_TO_EMAIL` | Recipient address for the brief |
| `ANTHROPIC_API_KEY` | From [console.anthropic.com](https://console.anthropic.com) |

---

## Running Locally

```bash
npm install
cp .env.example .env   # fill in all values
npm start
```

---

## How the Token Rotation Works

- On every run, `getMicrosoftAccessToken()` exchanges the stored refresh token
  for a fresh access token. Access tokens expire in ~1 hour; the refresh token
  is long-lived and stays active as long as the cron runs at least weekly.
- If Microsoft ever rotates the refresh token (rare for active apps), the new
  value is printed to the Railway build log with the prefix
  `NEW REFRESH TOKEN (update MICROSOFT_REFRESH_TOKEN in Railway):`.
  Update the env var promptly when you see that message.
- If the token refresh fails entirely, the script sends a failure email with
  subject `Weekly Brief FAILED — MS token refresh failed` and exits non-zero.
