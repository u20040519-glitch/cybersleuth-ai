// =============================================================================
// CYBERSLEUTH AI - Browser smoke test
// =============================================================================
// Drives a headless Chrome through the login flow of the published demo, so
// a broken demo is caught the way a visitor would hit it:
//
//   1. the page loads,
//   2. the API status indicator reports the backend,
//   3. the credentials are accepted and the app lands on the dashboard.
//
// It talks to Chrome through the DevTools protocol, so no test framework and
// no npm dependency is needed.
//
// Usage:
//   node scripts/browser_smoke_test.mjs
//   node scripts/browser_smoke_test.mjs --url https://example.com --email a@b.c --password secret
// =============================================================================

import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

function parseArgs(argv) {
  const args = {
    url: 'https://u20040519-glitch.github.io/cybersleuth-ai/login',
    email: 'investigator@cybersleuth.ai',
    password: 'Investigator!2026',
    chrome:
      process.env.CHROME_PATH ||
      'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  }
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === '--url') args.url = argv[++i] ?? args.url
    else if (arg === '--email') args.email = argv[++i] ?? args.email
    else if (arg === '--password') args.password = argv[++i] ?? args.password
    else if (arg === '--chrome') args.chrome = argv[++i] ?? args.chrome
  }
  return args
}

const args = parseArgs(process.argv.slice(2))

if (!existsSync(args.chrome)) {
  console.error(`Chrome was not found at ${args.chrome}. Set CHROME_PATH.`)
  process.exit(2)
}

const profile = await mkdtemp(join(tmpdir(), 'cybersleuth-smoke-'))
const port = 9333

const chrome = spawn(
  args.chrome,
  [
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    '--no-first-run',
    '--disable-extensions',
    `--user-data-dir=${profile}`,
    `--remote-debugging-port=${port}`,
    'about:blank',
  ],
  { stdio: 'ignore' },
)

const cleanup = async () => {
  chrome.kill()
  // Chrome releases the profile directory a moment after it is stopped; on
  // Windows the files are still locked for a short while.
  await new Promise((resolve) => setTimeout(resolve, 800))
  try {
    await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 300 })
  } catch {
    // A leftover temporary profile is not worth failing the test over.
  }
}

async function waitForDevTools() {
  for (let i = 0; i < 60; i += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`)
      if (response.ok) return
    } catch {
      // Not up yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error('Chrome did not start the DevTools endpoint')
}

await waitForDevTools()

const tab = await (
  await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(args.url)}`, {
    method: 'PUT',
  })
).json()

const socket = new WebSocket(tab.webSocketDebuggerUrl)
let nextId = 1
const pending = new Map()

socket.addEventListener('message', (event) => {
  const message = JSON.parse(event.data)
  if (message.id && pending.has(message.id)) {
    const { resolve, reject } = pending.get(message.id)
    pending.delete(message.id)
    if (message.error) reject(new Error(message.error.message))
    else resolve(message.result)
  }
})

await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve)
  socket.addEventListener('error', reject)
})

function send(method, params = {}) {
  const id = nextId++
  socket.send(JSON.stringify({ id, method, params }))
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }))
}

async function evaluate(expression) {
  const result = await send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  })
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text ?? 'evaluation failed')
  }
  return result.result.value
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

try {
  await send('Runtime.enable')
  await send('Page.enable')

  // 1. the page loads
  await wait(4000)
  const title = await evaluate('document.title')
  console.log(`page loaded: ${title}`)

  // 2. the API status indicator
  const status = await evaluate(`(() => {
    const el = [...document.querySelectorAll('[role="status"]')].find((n) => /API|Checking/.test(n.textContent || ''))
    return el ? el.textContent.trim().replace(/\\s+/g, ' ') : null
  })()`)
  console.log(`api status: ${status ?? 'no indicator found'}`)

  // 3. the login
  const filled = await evaluate(`(() => {
    const setValue = (element, value) => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
      setter.call(element, value)
      element.dispatchEvent(new Event('input', { bubbles: true }))
      element.dispatchEvent(new Event('change', { bubbles: true }))
    }
    const email = document.querySelector('input[name="email"]')
    const password = document.querySelector('input[name="password"]')
    if (!email || !password) return false
    setValue(email, ${JSON.stringify(args.email)})
    setValue(password, ${JSON.stringify(args.password)})
    return true
  })()`)

  if (!filled) throw new Error('the login form was not found')
  console.log('credentials entered')

  await evaluate(`(() => {
    const form = document.querySelector('form')
    form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  })()`)

  // The dashboard is the destination of a successful login.
  let result = null
  for (let i = 0; i < 20; i += 1) {
    await wait(1000)
    result = await evaluate(`(() => {
      const error = document.querySelector('[data-testid="login-error"]')
      const status = document.querySelector('[role="status"]')
      return {
        path: location.pathname,
        hasToken: !!localStorage.getItem('cybersleuth_access_token'),
        error: error ? error.textContent.trim().replace(/\\s+/g, ' ') : null,
        apiStatus: status ? status.textContent.trim().replace(/\\s+/g, ' ').slice(0, 120) : null,
      }
    })()`)
    if (result.hasToken || result.error) break
  }

  console.log(`result: ${JSON.stringify(result)}`)

  if (result?.hasToken && result.path.endsWith('/dashboard')) {
    console.log('\nPASS - the demo is reachable and the credentials work.')
    await cleanup()
    process.exit(0)
  }

  console.log('\nFAIL - see the result above.')
  await cleanup()
  process.exit(1)
} catch (error) {
  console.error('FAIL -', error.message)
  await cleanup()
  process.exit(1)
}
