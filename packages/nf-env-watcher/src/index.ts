import type { Context } from '@deepseek-ai/cordis'
import { watch, readFileSync, existsSync, appendFileSync, mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { parseEnv } from 'node:util'

export const name = 'nf-env-watcher'
export const inject = ['logger']

/* ------------------------------------------------------------------ *
 * Bootstrap-only mirror of @deepseek-ai/dsh-app-boot BOOTSTRAP_NAMES
 * and BOOTSTRAP_PREFIXES. If <cwd>/.env declares any of these, reload
 * is hard-rejected (consistent with dsh-app-boot's own .env loader).
 * ------------------------------------------------------------------ */
const BOOTSTRAP_NAMES = new Set([
  'PATH', 'HOME', 'USERPROFILE', 'SHELL', 'NODE_OPTIONS', 'NODE_PATH',
  'NODE_EXTRA_CA_CERTS', 'LD_PRELOAD', 'LD_LIBRARY_PATH', 'LD_AUDIT',
  'BASH_ENV', 'ENV', 'SHELLOPTS', 'BASHOPTS', 'PERL5OPT', 'PERL5LIB',
  'PYTHONSTARTUP', 'PYTHONPATH', 'RUBYOPT', 'RUBYLIB', 'JAVA_TOOL_OPTIONS',
  '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS', 'PYTHONHOME', 'GIT_SSH',
  'GIT_SSH_COMMAND', 'GIT_EXTERNAL_DIFF', 'GIT_PAGER', 'GIT_EDITOR',
  'GIT_ASKPASS', 'SSH_ASKPASS', 'GIT_CONFIG_GLOBAL', 'GIT_CONFIG_SYSTEM',
  'GIT_CONFIG_COUNT', 'EDITOR', 'VISUAL', 'PAGER', 'BROWSER',
  'DEEPSEEK_BASE_URL', 'DEEPSEEK_SEARCH_BASE_URL', 'SSL_CERT_FILE',
  'SSL_CERT_DIR', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
  'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'NODE_TLS_REJECT_UNAUTHORIZED',
])
const BOOTSTRAP_PREFIXES = ['DSH_', 'XDG_', 'DYLD_', 'BASH_FUNC_']

function isBootstrapOnly(name: string): boolean {
  const upper = name.toUpperCase()
  if (BOOTSTRAP_NAMES.has(upper)) return true
  return BOOTSTRAP_PREFIXES.some((p) => upper.startsWith(p))
}

/* ------------------------------------------------------------------ *
 * Read + parse <cwd>/.env. Returns:
 *   { ok: true,  values }
 *   { ok: false, error, offendingKey? }    when a bootstrap-only key is present
 *   { ok: false, error }                   when file missing or unreadable
 * ------------------------------------------------------------------ */
type ReloadResult =
  | { ok: true; values: Record<string, string> }
  | { ok: false; error: string; offendingKey?: string }

function readEnvFile(file: string): ReloadResult {
  if (!existsSync(file)) {
    return { ok: false, error: 'file missing' }
  }
  let content: string
  try {
    content = readFileSync(file, 'utf8')
  } catch (e) {
    return { ok: false, error: 'unreadable: ' + (e instanceof Error ? e.message : String(e)) }
  }
  let values: Record<string, string>
  try {
    values = parseEnv(content)
  } catch (e) {
    return { ok: false, error: 'parse error: ' + (e instanceof Error ? e.message : String(e)) }
  }
  for (const k of Object.keys(values)) {
    if (isBootstrapOnly(k)) {
      return {
        ok: false,
        error: `<cwd>/.env declares bootstrap-only variable "${k}"; bootstrap-only vars must come from the launching environment (export $k=... in your shell), not from .env. Reload rejected.`,
        offendingKey: k,
      }
    }
  }
  return { ok: true, values }
}

function applyToProcessEnv(values: Record<string, string>): string[] {
  const applied: string[] = []
  for (const [k, v] of Object.entries(values)) {
    // Policy: override every key, including ones inherited from the
    // launching shell. .env is the single source of truth at runtime.
    if (process.env[k] !== v) {
      process.env[k] = v
      applied.push(k)
    }
  }
  return applied
}

/* ------------------------------------------------------------------ *
 * Activity log: append-only JSONL under <cwd>/runtime/nf-env-watcher.log
 * so the agent (and humans) can see reload history without owning
 * dsh's stderr.
 * ------------------------------------------------------------------ */
const logFile = join(process.cwd(), 'runtime', 'nf-env-watcher.log')
try { mkdirSync(dirname(logFile), { recursive: true }) } catch { /* ignore */ }

function logEvent(event: string, fields: Record<string, unknown>): void {
  try {
    appendFileSync(logFile, JSON.stringify({ ts: new Date().toISOString(), event, ...fields }) + '\n', 'utf8')
  } catch {
    /* log failures must never break the watcher */
  }
}

export function apply(ctx: Context) {
  // `logger` is a built-in property of every Cordis Context — callable form
  // ctx.logger(name) returns a named logger facade.
  const logger = ctx.logger?.('nf-env-watcher')
  const envFile = join(process.cwd(), '.env')
  logger?.info(`[nf-env-watcher] watching ${envFile} (debounce 200ms)`)
  logEvent('start', { envFile, cwd: process.cwd() })

  // Initial read: if .env exists, apply it now. (dsh-app-boot already loaded
  // the inherited .env into process.env during boot; this syncs any
  // difference and catches changes made between boot and apply().)
  const initial = readEnvFile(envFile)
  if (initial.ok) {
    const applied = applyToProcessEnv(initial.values)
    if (applied.length > 0) {
      logger?.info(`[nf-env-watcher] initial sync: applied ${applied.length} key(s): ${applied.join(', ')}`)
      logEvent('initial-sync', { applied })
    }
  } else if ('error' in initial && initial.error !== 'file missing') {
    logger?.warn(`[nf-env-watcher] initial read failed: ${initial.error}`)
    logEvent('initial-error', { error: initial.error })
  }

  // fs.watch + debounce. Raw fs.watch on Windows can fire several events
  // for one editor save; debouncing collapses them.
  let debounceTimer: NodeJS.Timeout | null = null
  const DEBOUNCE_MS = 200

  const handleChange = () => {
    if (debounceTimer !== null) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      debounceTimer = null
      const result = readEnvFile(envFile)
      if (!result.ok && 'error' in result) {
        // "file missing" can fire briefly when editors save by atomic
        // rename; ignore that one. Other failures are logged.
        if (result.error !== 'file missing') {
          logger?.warn(`[nf-env-watcher] reload rejected: ${result.error}`)
          logEvent('reject', { error: result.error, offendingKey: result.offendingKey })
        }
        return
      }
      const applied = applyToProcessEnv(result.values)
      if (applied.length > 0) {
        logger?.info(`[nf-env-watcher] hot-reload: applied ${applied.length} key(s): ${applied.join(', ')}`)
        logEvent('reload', { applied })
      } else {
        logger?.debug(`[nf-env-watcher] reload: no changes`)
      }
    }, DEBOUNCE_MS)
  }

  let watcher: ReturnType<typeof watch> | null = null
  try {
    watcher = watch(envFile, { persistent: true }, (_eventType) => {
      handleChange()
    })
    watcher.on('error', (err) => {
      // ENOENT fires when the file is deleted after we started watching;
      // ignore. Other errors get logged.
      if ((err as NodeJS.ErrnoException).code !== 'ENOENT') {
        logger?.warn(`[nf-env-watcher] watch error: ${err.message}`)
      }
    })
  } catch (e) {
    logger?.warn(`[nf-env-watcher] cannot watch ${envFile}: ${e instanceof Error ? e.message : String(e)}`)
  }

  ctx.effect(() => () => {
    if (debounceTimer !== null) clearTimeout(debounceTimer)
    if (watcher !== null) {
      try { watcher.close() } catch { /* swallow */ }
    }
    logger?.info('[nf-env-watcher] stopped watching .env')
    logEvent('stop', {})
  }, 'nf-env-watcher: shutdown')
}
