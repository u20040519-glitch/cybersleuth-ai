// =============================================================================
// CYBERSLEUTH AI - Publish the frontend to GitHub Pages
// =============================================================================
// The Netlify site of this repository belongs to a team whose plan forces
// "Members only" visibility, so it cannot be used as a public demo. GitHub
// Pages serves the same build straight from the repository, without an access
// wall, and it keeps working when this machine is switched off.
//
// The script:
//
//   1. builds the frontend with the public base path of the Pages site
//      (/<repo>/) and the API location to use;
//   2. writes runtime-config.js into the build, so the API address can be
//      changed later without a rebuild;
//   3. publishes the build to the `gh-pages` branch of the repository.
//
// Usage:
//   node scripts/deploy_github_pages.mjs
//   node scripts/deploy_github_pages.mjs --api-base-url https://example.com/api
//   node scripts/deploy_github_pages.mjs --api-base-url https://example.com/api --dry-run
//
// Options:
//   --api-base-url   Absolute URL of the API, including the /api prefix.
//                    Omit it to use the same origin as the page (which is
//                    what the Netlify redirect rule and the Vite proxy do).
//   --repo           owner/name of the repository (default: the origin remote)
//   --branch         branch to publish to (default: gh-pages)
//   --dry-run        build everything, but do not touch git
// =============================================================================

import { execFileSync } from 'node:child_process'
import { cp, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const frontendDir = join(repoRoot, 'frontend')
// The Pages build goes into its own directory, so the local build in
// frontend/dist (used by the dev/preview server and the tunneled demo)
// stays untouched.
const distDir = join(frontendDir, 'dist-pages')

// ---------------------------------------------------------------------------
// Arguments
// ---------------------------------------------------------------------------
function parseArgs(argv) {
  const args = { apiBaseUrl: '', repo: '', branch: 'gh-pages', dryRun: false }
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === '--api-base-url') args.apiBaseUrl = argv[++i] ?? ''
    else if (arg === '--repo') args.repo = argv[++i] ?? ''
    else if (arg === '--branch') args.branch = argv[++i] ?? ''
    else if (arg === '--dry-run') args.dryRun = true
    else throw new Error(`Unknown argument: ${arg}`)
  }
  return args
}

const args = parseArgs(process.argv.slice(2))

function git(argsList, options = {}) {
  const result = execFileSync('git', argsList, {
    cwd: repoRoot,
    encoding: 'utf8',
    stdio: options.capture === false ? 'inherit' : 'pipe',
  })
  return (result ?? '').trim()
}

// ---------------------------------------------------------------------------
// Repository
// ---------------------------------------------------------------------------
if (!args.repo) {
  const remote = git(['remote', 'get-url', 'origin'])
  const match = remote.match(/github\.com[/:]([^/]+)\/([^/\s]+?)(?:\.git)?$/)
  if (!match) throw new Error(`Could not read the repository from the origin remote: ${remote}`)
  args.repo = `${match[1]}/${match[2]}`
}

const [owner, repoName] = args.repo.split('/')
const basePath = `/${repoName}/`

console.log(`Repository : ${args.repo}`)
console.log(`Branch     : ${args.branch}`)
console.log(`Base path  : ${basePath}`)

// ---------------------------------------------------------------------------
// 1. Build
// ---------------------------------------------------------------------------
console.log('\n[1/4] building the frontend ...')
// On Windows npm is a .cmd shim, which cannot be executed directly.
const isWindows = process.platform === 'win32'
const npm = isWindows ? 'npm.cmd' : 'npm'

// GitHub Pages publishes the branch with a build that takes a few minutes.
// The app therefore also reads the same configuration file straight from the
// repository, which is current within seconds.
const rawConfigUrl = `https://raw.githubusercontent.com/${owner}/${repoName}/${args.branch}/runtime-config.js`

execFileSync(npm, ['run', 'build:pages'], {
  cwd: frontendDir,
  stdio: 'inherit',
  // Node refuses to spawn a .cmd without a shell since the CVE-2024-27980 fix.
  shell: isWindows,
  env: {
    ...process.env,
    VITE_BASE_PATH: basePath,
    VITE_API_BASE_URL: args.apiBaseUrl,
    VITE_PAGES_CONFIG_URL: rawConfigUrl,
  },
})

// ---------------------------------------------------------------------------
// 2. Runtime configuration
// ---------------------------------------------------------------------------
console.log('\n[2/4] writing the runtime configuration ...')
const runtimeConfig = `// Generated by scripts/deploy_github_pages.mjs - do not edit by hand.
// The API addresses are tried in order; the first one that answers /health
// is used. '/api' is the same origin and is always the last candidate.
window.__CYBERSLEUTH_CONFIG__ = {
  apiBaseUrls: ${JSON.stringify([args.apiBaseUrl, '/api'].filter(Boolean))},
}
`
await writeFile(join(distDir, 'runtime-config.js'), runtimeConfig, 'utf8')

// GitHub Pages runs Jekyll by default; a file without an extension would be
// dropped. The marker turns that off.
await writeFile(join(distDir, '.nojekyll'), '', 'utf8')

// ---------------------------------------------------------------------------
// 3. Publish
// ---------------------------------------------------------------------------
if (args.dryRun) {
  console.log('\n[3/4] dry run - the git branch is left untouched')
  console.log(`[4/4] the build is in ${distDir}`)
  process.exit(0)
}

console.log('\n[3/4] publishing to the branch ...')
const worktree = await mkdtemp(join(tmpdir(), 'cybersleuth-pages-'))
// A unique orphan branch is used, because `git checkout --orphan` refuses to
// reuse a branch that already exists in the repository.
const tempBranch = `pages-publish-${Date.now()}`
try {
  git(['worktree', 'add', '--detach', worktree])

  const inWorktree = (argsList) =>
    execFileSync('git', argsList, { cwd: worktree, encoding: 'utf8', stdio: 'pipe' }).trim()

  inWorktree(['checkout', '--orphan', tempBranch])
  inWorktree(['rm', '-rf', '--cached', '.'])
  // Everything in the worktree is replaced by the build output.
  for (const entry of await (await import('node:fs/promises')).readdir(worktree)) {
    if (entry === '.git') continue
    await rm(join(worktree, entry), { recursive: true, force: true })
  }
  await cp(distDir, worktree, { recursive: true })

  inWorktree(['add', '-A'])
  inWorktree(['commit', '-m', `deploy: publish the frontend to ${args.branch}`])
  inWorktree(['branch', '-f', args.branch, tempBranch])
  inWorktree(['push', '--force', 'origin', `${args.branch}:${args.branch}`])

  console.log(`[4/4] pushed to ${args.branch}`)
} finally {
  git(['worktree', 'remove', '--force', worktree], { capture: false })
  await rm(worktree, { recursive: true, force: true })
  // The temporary branch can only be deleted once the worktree is gone.
  try {
    git(['branch', '-D', tempBranch])
  } catch {
    // Nothing to clean up.
  }
}

// ---------------------------------------------------------------------------
// 5. Enable GitHub Pages
// ---------------------------------------------------------------------------
console.log('\n[5/5] enabling GitHub Pages ...')
const pagesUrl = `https://${owner}.github.io/${repoName}/`
try {
  // The response is read without --silent: the flag would swallow the JSON.
  const existing = JSON.parse(
    execFileSync('gh', ['api', `repos/${args.repo}/pages`], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    }),
  )
  console.log(`GitHub Pages is already enabled: ${existing.html_url || pagesUrl}`)
} catch {
  try {
    execFileSync(
      'gh',
      [
        'api',
        '--method',
        'POST',
        `repos/${args.repo}/pages`,
        '--input',
        '-',
      ],
      {
        input: JSON.stringify({ source: { branch: args.branch, path: '/' } }),
        stdio: ['pipe', 'inherit', 'pipe'],
      },
    )
    console.log('GitHub Pages enabled')
  } catch (error) {
    const output = `${error.stdout ?? ''}${error.stderr ?? ''}`
    if (output.includes('already enabled')) {
      console.log('GitHub Pages is already enabled')
    } else {
      throw error
    }
  }
}

console.log(`\nDone. The demo will be available at ${pagesUrl}`)
