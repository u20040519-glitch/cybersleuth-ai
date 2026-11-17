// =============================================================================
// CYBERSLEUTH AI - Demo flow test
// =============================================================================
// Walks through the exact paths a reviewer takes in the published demo:
//
//   1. open the SpyTrace page, pick the seeded case and the APK
//   2. run the analysis, wait for the findings panel
//   3. assert the real findings appear (not an error banner, not an empty
//      state) -- this is the flow that used to fail with "Analysis failed"
//
// Usage:
//   node scripts/browser_demo_flow.mjs
//   node scripts/browser_demo_flow.mjs --url https://u20040519-glitch.github.io/cybersleuth-ai/spytrace
// =============================================================================

import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

function parseArgs(argv) {
  const args = {
    url: 'https://u20040519-glitch.github.io/cybersleuth-ai/spytrace',
    chrome:
      process.env.CHROME_PATH ||
      'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    email: 'investigator@cybersleuth.ai',
    password: 'Investigator!2026',
  }
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === '--url') args.url = argv[++i] ?? args.url
    else if (arg === '--chrome') args.chrome = argv[++i] ?? args.chrome
    else if (arg === '--email') args.email = argv[++i] ?? args.email
    else if (arg === '--password') args.password = argv[++i] ?? args.password
  }
  return args
}

const args = parseArgs(process.argv.slice(2))
if (!existsSync(args.chrome)) {
  console.error(`Chrome was not found at ${args.chrome}. Set CHROME_PATH.`)
  process.exit(2)
}

const profile = await mkdtemp(join(tmpdir(), 'cybersleuth-flow-'))
const port = 9444

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
  await new Promise((resolve) => setTimeout(resolve, 800))
  try {
    await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 300 })
  } catch {
    // not worth failing a test trip over
  }
}

async function waitForDevTools() {
  for (let i = 0; i < 60; i += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`)
      if (response.ok) return
    } catch {
      // not up yet
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
const check = (name, condition) =>
  console.log(`  ${condition ? 'PASS' : 'FAIL'}  ${name}`)

try {
  await send('Runtime.enable')

  // 1. open the login page (derived from the target url)
  const target = args.url
  const basePath = target.replace(/\/[^/]*$/, '/')
  const loginUrl = `${basePath}login`
  await send('Page.enable')
  await send('Page.navigate', { url: loginUrl })
  await wait(2000)
  // 2. wait for the login form
  let isLogin = false
  for (let i = 0; i < 40 && !isLogin; i += 1) {
    isLogin = await evaluate('!!document.querySelector(\'input[name="email"]\')')
    if (!isLogin) await wait(500)
  }
  const title = await evaluate('document.title')
  console.log(`page: ${title} @ ${await evaluate('location.pathname')} (isLogin=${isLogin})`)

  if (isLogin) {
    const filled = await evaluate(`(() => {
      const setValue = (el, value) => {
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
        setter.call(el, value)
        el.dispatchEvent(new Event('input', { bubbles: true }))
        el.dispatchEvent(new Event('change', { bubbles: true }))
      }
      const email = document.querySelector('input[name="email"]')
      const password = document.querySelector('input[name="password"]')
      setValue(email, ${JSON.stringify(args.email)})
      setValue(password, ${JSON.stringify(args.password)})
      return true
    })()`)
    await evaluate(`(() => {
      const form = document.querySelector('form')
      form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    })()`)
    await wait(4000)
    const state = await evaluate(`(() => ({
      path: location.pathname,
      token: !!localStorage.getItem('cybersleuth_access_token'),
      error: (document.querySelector('[data-testid="login-error"]') || {}).textContent || null,
    }))()`)
    console.log(`after login: ${JSON.stringify(state)}`)
  }

  // 3. open the SpyTrace page
  await send('Page.enable')
  await send('Page.navigate', { url: args.url })
  await wait(5000)
  console.log(`spytrace page: @ ${await evaluate('location.pathname')}`)

  // 4. wait for the SpyTrace launcher
  let ready = false
  for (let i = 0; i < 40 && !ready; i += 1) {
    await wait(500)
    ready = await evaluate('!!document.querySelector(\'#investigation-select\')')
  }
  if (!ready) {
    const text = await evaluate('document.body.innerText.replace(/\\s+/g, \' \').slice(0, 300)')
    throw new Error(`the module launcher did not render; page text: ${text}`)
  }
  console.log('module launcher rendered')

  // 4. pick the seeded case (the APK belongs to CASE-2026-0147)
  const caseSelected = await evaluate(`(() => {
    const select = document.querySelector('#investigation-select')
    const option = [...select.options].find((o) => /CASE-2026-0147/.test(o.textContent || ''))
      || [...select.options].find((o) => o.value)
    if (!option) return false
    select.value = option.value
    select.dispatchEvent(new Event('change', { bubbles: true }))
    return option.textContent
  })()`)
  console.log(`case selected: ${caseSelected}`)

  // 5. pick the APK
  let evidence = false
  for (let i = 0; i < 20 && !evidence; i += 1) {
    await wait(400)
    evidence = await evaluate(`(() => {
      const select = document.querySelector('#evidence-select')
      const option = [...select.options].find((o) => /\\.apk$/i.test(o.textContent || ''))
      if (!option) return false
      select.value = option.value
      select.dispatchEvent(new Event('change', { bubbles: true }))
      return option.textContent
    })()`)
  }
  console.log(`evidence selected: ${evidence || 'none found'}`)

  // 6. run the analysis
  await evaluate(`(() => {
    const button = [...document.querySelectorAll('button')].find((b) => /Run Forensic Analysis/.test(b.textContent || ''))
    button.click()
  })()`)

  // 7. wait for the findings panel
  let findings = false
  for (let i = 0; i < 20 && !findings; i += 1) {
    await wait(600)
    findings = await evaluate('document.body.innerText.includes(\'Embedded network endpoints\')')
  }

  const failure = await evaluate(`(() => {
    const banner = [...document.querySelectorAll('p')].find((el) => /Analysis failed/.test(el.textContent || ''))
    return banner ? banner.textContent : null
  })()`)
  const hasFindings = await evaluate('document.body.innerText.includes(\'Embedded network endpoints\')')
  const hasRisk = await evaluate('document.body.innerText.includes(\'Risk score\')')
  const summary = await evaluate(`(() => {
    const el = [...document.querySelectorAll('p')].find((n) => /analysed statically/.test(n.textContent || ''))
    return el ? el.textContent.trim() : null
  })()`)

  console.log('\nResult:')
  check('findings panel rendered ("Embedded network endpoints")', hasFindings)
  check('risk band rendered ("Risk score")', hasRisk)
  check('no "Analysis failed" banner', !failure)
  console.log(`  summary: ${summary ?? 'n/a'}`)

  await cleanup()
  process.exit(hasFindings && !failure ? 0 : 1)
} catch (error) {
  console.error('FAIL -', error.message)
  await cleanup()
  process.exit(1)
}
