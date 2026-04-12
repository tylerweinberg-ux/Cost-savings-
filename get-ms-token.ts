/**
 * get-ms-token.ts
 *
 * Run this ONCE locally to obtain the initial Microsoft OAuth2 refresh token.
 *
 *   npx tsx get-ms-token.ts
 *
 * It spins up a local Express server on port 3000, opens your browser to the
 * Microsoft consent page, catches the callback, exchanges the code for tokens,
 * and prints the refresh token to the console.
 *
 * Copy the printed MICROSOFT_REFRESH_TOKEN value into your Railway env vars.
 * You will not need to run this script again unless you revoke access.
 */

import express from 'express'
import { createServer } from 'http'
import * as dotenv from 'dotenv'

dotenv.config()

const CLIENT_ID = process.env.MICROSOFT_CLIENT_ID
const CLIENT_SECRET = process.env.MICROSOFT_CLIENT_SECRET
const TENANT_ID = process.env.MICROSOFT_TENANT_ID ?? 'common'
const REDIRECT_URI = 'http://localhost:3000/callback'
const SCOPE =
  'https://graph.microsoft.com/Calendars.Read https://graph.microsoft.com/Mail.Read offline_access'
const PORT = 3000

if (!CLIENT_ID || !CLIENT_SECRET) {
  console.error(
    'ERROR: MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET must be set in .env'
  )
  process.exit(1)
}

const authUrl = new URL(
  `https://login.microsoftonline.com/${TENANT_ID}/oauth2/v2.0/authorize`
)
authUrl.searchParams.set('client_id', CLIENT_ID)
authUrl.searchParams.set('response_type', 'code')
authUrl.searchParams.set('redirect_uri', REDIRECT_URI)
authUrl.searchParams.set('scope', SCOPE)
authUrl.searchParams.set('access_type', 'offline')
authUrl.searchParams.set('prompt', 'consent')

const app = express()
const server = createServer(app)

app.get('/callback', async (req, res) => {
  const code = req.query.code as string | undefined
  const error = req.query.error as string | undefined

  if (error) {
    const desc = req.query.error_description ?? ''
    res.send(`<h2>OAuth error: ${error}</h2><pre>${desc}</pre>`)
    server.close()
    return
  }

  if (!code) {
    res.send('<h2>Error: No authorization code received.</h2>')
    server.close()
    return
  }

  try {
    const params = new URLSearchParams({
      client_id: CLIENT_ID!,
      client_secret: CLIENT_SECRET!,
      code,
      redirect_uri: REDIRECT_URI,
      grant_type: 'authorization_code',
    })

    const tokenRes = await fetch(
      `https://login.microsoftonline.com/${TENANT_ID}/oauth2/v2.0/token`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params,
      }
    )

    const data = await tokenRes.json()

    if (!data.refresh_token) {
      res.send(
        `<h2>Error: No refresh token in response.</h2>` +
          `<p>Make sure the app requests <code>offline_access</code> scope and ` +
          `<code>prompt=consent</code> was included in the auth URL.</p>` +
          `<pre>${JSON.stringify(data, null, 2)}</pre>`
      )
      server.close()
      return
    }

    console.log('\n=========================================')
    console.log('SUCCESS! Add this to Railway environment variables:')
    console.log('=========================================')
    console.log(`\nMICROSOFT_REFRESH_TOKEN=${data.refresh_token}\n`)
    console.log('=========================================')

    res.send(
      `<h2>Authorization successful!</h2>` +
        `<p>Check your terminal for the <code>MICROSOFT_REFRESH_TOKEN</code> value.</p>` +
        `<p>Copy it to your Railway environment variables, then close this tab.</p>`
    )

    server.close(() => process.exit(0))
  } catch (err) {
    console.error('Token exchange failed:', err)
    res.send(`<h2>Error during token exchange.</h2><pre>${err}</pre>`)
    server.close()
  }
})

server.listen(PORT, async () => {
  console.log(`Local OAuth server running at http://localhost:${PORT}`)
  console.log('\nOpening browser for Microsoft OAuth consent...\n')
  console.log('If the browser does not open automatically, visit this URL:')
  console.log('\n' + authUrl.toString() + '\n')

  // Attempt to open the browser; silently ignore if the `open` package is absent.
  try {
    const { default: open } = await import('open')
    await open(authUrl.toString())
  } catch {
    // `open` is optional — user can navigate manually.
  }
})
