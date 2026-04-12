import Anthropic from '@anthropic-ai/sdk'
import nodemailer from 'nodemailer'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CalendarEvent {
  id: string
  subject: string
  start: { dateTime: string; timeZone: string }
  end: { dateTime: string; timeZone: string }
  location?: { displayName: string }
  organizer?: { emailAddress: { name: string; address: string } }
}

interface Message {
  id: string
  subject: string
  from: { emailAddress: { name: string; address: string } }
  receivedDateTime: string
  bodyPreview: string
  isRead: boolean
}

// ---------------------------------------------------------------------------
// OAuth2 refresh-token flow — obtains a fresh access token on every run
// ---------------------------------------------------------------------------

async function getMicrosoftAccessToken(): Promise<string> {
  const params = new URLSearchParams({
    client_id: process.env.MICROSOFT_CLIENT_ID!,
    client_secret: process.env.MICROSOFT_CLIENT_SECRET!,
    refresh_token: process.env.MICROSOFT_REFRESH_TOKEN!,
    grant_type: 'refresh_token',
    scope:
      'https://graph.microsoft.com/Calendars.Read https://graph.microsoft.com/Mail.Read offline_access',
  })

  const res = await fetch(
    `https://login.microsoftonline.com/${process.env.MICROSOFT_TENANT_ID}/oauth2/v2.0/token`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: params,
    }
  )

  const data = await res.json()
  if (!data.access_token)
    throw new Error(`MS token refresh failed: ${JSON.stringify(data)}`)

  // Microsoft occasionally rotates the refresh token. Log it so the user can
  // update the Railway env var before the old one expires.
  if (
    data.refresh_token &&
    data.refresh_token !== process.env.MICROSOFT_REFRESH_TOKEN
  ) {
    console.log(
      'NEW REFRESH TOKEN (update MICROSOFT_REFRESH_TOKEN in Railway):',
      data.refresh_token
    )
  }

  return data.access_token
}

// ---------------------------------------------------------------------------
// Microsoft Graph fetchers
// ---------------------------------------------------------------------------

async function fetchCalendarEvents(
  token: string
): Promise<CalendarEvent[]> {
  const now = new Date()
  const weekFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)

  const params = new URLSearchParams({
    startDateTime: now.toISOString(),
    endDateTime: weekFromNow.toISOString(),
    $select: 'id,subject,start,end,location,organizer',
    $orderby: 'start/dateTime',
    $top: '50',
  })

  const res = await fetch(
    `https://graph.microsoft.com/v1.0/me/calendarView?${params}`,
    { headers: { Authorization: `Bearer ${token}` } }
  )

  if (!res.ok)
    throw new Error(`Calendar fetch failed: ${res.status} ${await res.text()}`)

  const data = await res.json()
  return (data.value ?? []) as CalendarEvent[]
}

async function fetchUnreadEmails(token: string): Promise<Message[]> {
  const params = new URLSearchParams({
    $filter: 'isRead eq false',
    $select: 'id,subject,from,receivedDateTime,bodyPreview,isRead',
    $orderby: 'receivedDateTime desc',
    $top: '20',
  })

  const res = await fetch(
    `https://graph.microsoft.com/v1.0/me/messages?${params}`,
    { headers: { Authorization: `Bearer ${token}` } }
  )

  if (!res.ok)
    throw new Error(`Email fetch failed: ${res.status} ${await res.text()}`)

  const data = await res.json()
  return (data.value ?? []) as Message[]
}

// ---------------------------------------------------------------------------
// Email sender (SMTP via nodemailer)
// ---------------------------------------------------------------------------

async function sendEmail(subject: string, html: string): Promise<void> {
  const transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: Number(process.env.SMTP_PORT ?? 587),
    secure: process.env.SMTP_SECURE === 'true',
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS,
    },
  })

  await transporter.sendMail({
    from: process.env.BRIEF_FROM_EMAIL,
    to: process.env.BRIEF_TO_EMAIL,
    subject,
    html,
  })
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function runBrief(): Promise<void> {
  // Obtain a fresh access token via the refresh-token grant.
  // On failure, send an error email and exit — never proceed with an empty token.
  let msToken: string
  try {
    msToken = await getMicrosoftAccessToken()
  } catch (err) {
    console.error('MS token refresh failed:', err)
    try {
      await sendEmail(
        'Weekly Brief FAILED \u2014 MS token refresh failed',
        `<p>The weekly brief cron job failed to obtain a Microsoft Graph access token.</p>` +
          `<pre>${String(err)}</pre>` +
          `<p>Check the <code>MICROSOFT_REFRESH_TOKEN</code> Railway env var.</p>`
      )
    } catch (emailErr) {
      console.error('Also failed to send error email:', emailErr)
    }
    process.exit(1)
  }

  const [events, emails] = await Promise.all([
    fetchCalendarEvents(msToken),
    fetchUnreadEmails(msToken),
  ])

  const calendarText =
    events.length > 0
      ? events
          .map(
            (e) =>
              `- ${e.subject} | ${e.start.dateTime} \u2192 ${e.end.dateTime}` +
              (e.location?.displayName ? ` @ ${e.location.displayName}` : '')
          )
          .join('\n')
      : 'No upcoming events this week.'

  const emailText =
    emails.length > 0
      ? emails
          .map(
            (m) =>
              `- [${m.receivedDateTime}] From: ${m.from.emailAddress.name} <${m.from.emailAddress.address}>\n` +
              `  Subject: ${m.subject}\n` +
              `  Preview: ${m.bodyPreview}`
          )
          .join('\n\n')
      : 'No unread emails.'

  const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })

  const message = await anthropic.messages.create({
    model: 'claude-opus-4-6',
    max_tokens: 2048,
    messages: [
      {
        role: 'user',
        content:
          `You are generating a concise weekly brief email.\n\n` +
          `UPCOMING CALENDAR EVENTS (next 7 days):\n${calendarText}\n\n` +
          `UNREAD EMAILS (most recent 20):\n${emailText}\n\n` +
          `Please write a well-organized HTML weekly brief that:\n` +
          `1. Highlights key meetings and events for the week ahead\n` +
          `2. Summarizes important unread emails that likely need attention\n` +
          `3. Uses clear headings and bullet points\n` +
          `4. Is professional but friendly in tone\n` +
          `5. Returns only the HTML body content (no <html>/<head> wrapper needed)\n\n` +
          `Keep it concise \u2014 2\u20133 minutes to read.`,
      },
    ],
  })

  const briefHtml = (message.content[0] as { type: string; text: string }).text

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  await sendEmail(`Weekly Brief \u2014 ${today}`, briefHtml)
  console.log('Weekly brief sent successfully.')
}

runBrief().catch((err) => {
  console.error('Unhandled error in runBrief:', err)
  process.exit(1)
})
