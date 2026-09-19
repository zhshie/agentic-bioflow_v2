'use strict';
// The testable half of positron-bridge.
//
// Everything in this file is plain Node.js with no dependency on the
// `vscode`/`positron` modules, which only exist inside a running Positron
// window and cannot be imported by a standalone test process. `extension.ts`
// is the other half: it wires this logic to an HTTP server and to
// `positron.runtime.executeCode`, and is exercised only by hand (there is no
// way to stand up a Positron window in this repo's test suite, the same
// limit `scripts/positron_run.py`'s own header explains for why *that* file
// talks HTTP instead of importing a kallichore client).
//
// Splitting the logic out this way is what lets `tests/positron_bridge_test.sh`
// follow the repo's own rule - bash, exit code, no network - the same as
// every other test here, instead of being the one test that needs a real
// Positron to run at all.
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// --------------------------------------------------------------------------
// Loopback + token check
//
// Both checks fail closed: anything that does not affirmatively match a
// loopback address, or affirmatively match the token, is rejected. There is
// no default-allow branch in either function.
// --------------------------------------------------------------------------

/**
 * Is `addr` a loopback address, in any of the forms Node's `net` module
 * reports for one? IPv4 loopback is the whole 127.0.0.0/8 block, not just
 * 127.0.0.1 - and Node reports an IPv4 client on a dual-stack listener as
 * "::ffff:127.x.x.x", which a plain string-equals against "127.0.0.1" would
 * reject even though the connection never left the machine.
 */
function isLoopbackAddress(addr) {
  if (!addr) return false;
  const a = addr.startsWith('::ffff:') ? addr.slice(7) : addr;
  if (a === '::1') return true;
  const parts = a.split('.');
  return parts.length === 4 && parts[0] === '127';
}

/**
 * Does `authHeader` ("Bearer <token>") carry exactly `token`?
 *
 * Compared with `crypto.timingSafeEqual` rather than `===`: a `===` compare
 * on a bearer token returns slightly faster the earlier the strings diverge,
 * which is a real side channel against a token guessed a few bytes at a
 * time. Loopback-only narrows who can attempt that, but does not make the
 * comparison itself safe - another process on the same machine is still
 * "an attacker on loopback", and the fix costs nothing here.
 */
function checkToken(authHeader, token) {
  if (typeof authHeader !== 'string' || typeof token !== 'string' || !token) return false;
  const prefix = 'Bearer ';
  if (!authHeader.startsWith(prefix)) return false;
  const given = authHeader.slice(prefix.length);
  const a = Buffer.from(given, 'utf8');
  const b = Buffer.from(token, 'utf8');
  if (a.length !== b.length) {
    // timingSafeEqual throws on a length mismatch rather than returning
    // false, and the length itself must not be allowed to leak through a
    // caught-exception timing difference either - so this compares against
    // a same-length buffer instead of returning early.
    const padded = Buffer.alloc(b.length);
    a.copy(padded);
    return crypto.timingSafeEqual(padded, b) && a.length === b.length;
  }
  return crypto.timingSafeEqual(a, b);
}

// --------------------------------------------------------------------------
// State file path
//
// Never the project folder (PRINCIPLES.md invariant 11's own rule for the
// settings file applies here just as much: a folder a cloud drive syncs is
// not a safe place for a bearer token) and never a location this plugin
// invents - each OS already has one blessed "this machine, not this account,
// not synced anywhere" directory, and the point of this function is to name
// it rather than pick a new one.
// --------------------------------------------------------------------------

const STATE_SUBPATH = ['agentic-bioflow', 'positron-bridge.json'];

/**
 * Where the bridge file lives, given an environment and a platform.
 *
 * Takes both as arguments, rather than reading `process.env`/`process.platform`
 * directly, so a test can assert all three OS branches from one process -
 * the same reason `scripts/utils/portable.sh` exists as a file the rest of
 * this repo sources instead of each script re-detecting its own platform.
 */
function stateFilePath(env, platform) {
  if (platform === 'win32') {
    // %LOCALAPPDATA% is per-user and per-machine, and - unlike the Documents
    // folder many Windows accounts sync through OneDrive by default - is not
    // a folder anything syncs off this machine.
    const base = env.LOCALAPPDATA || path.join(env.USERPROFILE || '', 'AppData', 'Local');
    return path.join(base, ...STATE_SUBPATH);
  }
  // XDG Base Directory spec's state dir, honoured on macOS too: macOS has no
  // XDG convention of its own for "this machine, not synced", and
  // $XDG_STATE_HOME is respected by everything else in this repo that needs
  // the same property (scripts/fetch.sh stages under $XDG_CACHE_HOME for the
  // identical reason - never the project folder).
  const base = env.XDG_STATE_HOME || path.join(env.HOME || '', '.local', 'state');
  return path.join(base, ...STATE_SUBPATH);
}

// --------------------------------------------------------------------------
// Image diff
//
// The point of running code through the bridge instead of batch is the live
// console; the point of this diff is answering "what did that run draw"
// without shipping the console's full output back to the caller, which is
// the context-eating outcome T13 exists to avoid.
// --------------------------------------------------------------------------

const IMAGE_EXT = new Set(['.png', '.jpg', '.jpeg', '.svg', '.pdf', '.gif', '.tiff', '.tif']);

/**
 * Every image file under `dir`, as a map of relative path -> mtimeMs.
 *
 * Bounded depth (4) and a file-count cap (5000): this walks whatever
 * directory the session reports as its working directory, which on a real
 * project can contain `renv/` or `node_modules/`-sized trees, and a snapshot
 * taken before every run must stay cheap enough to take before every run.
 * Errors reading any one entry are skipped rather than failing the whole
 * snapshot - a permissions error on one subdirectory should not stop the
 * bridge from reporting the figures it can see.
 */
function listImages(dir, maxDepth = 4, maxFiles = 5000) {
  const found = new Map();
  if (!dir) return found;
  const stack = [{ d: dir, depth: 0 }];
  while (stack.length && found.size < maxFiles) {
    const { d, depth } = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(d, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      if (entry.name.startsWith('.')) continue; // skip .git, .Rproj.user, etc.
      const full = path.join(d, entry.name);
      if (entry.isDirectory()) {
        if (depth < maxDepth) stack.push({ d: full, depth: depth + 1 });
        continue;
      }
      if (!entry.isFile()) continue;
      if (!IMAGE_EXT.has(path.extname(entry.name).toLowerCase())) continue;
      try {
        found.set(full, fs.statSync(full).mtimeMs);
      } catch {
        // removed between readdir and stat; not a new image either way
      }
      if (found.size >= maxFiles) break;
    }
  }
  return found;
}

/**
 * Paths present in `after` that were absent from `before`, or whose mtime
 * moved forward - covers both "wrote a new file" and "overwrote figs/plot.png
 * again", which ggsave()/savefig() do by default and which a presence-only
 * diff would silently miss on every run after the first.
 */
function newImages(before, after) {
  const out = [];
  for (const [file, mtime] of after) {
    const prior = before.get(file);
    if (prior === undefined || mtime > prior) out.push(file);
  }
  return out.sort();
}

// --------------------------------------------------------------------------
// Result summary
//
// This is the entire reply body. No stdout, no stderr, no console
// transcript: those stay in Positron for the person looking at it, per the
// GitHub issue's own instruction not to let this eat the caller's context.
// --------------------------------------------------------------------------

/**
 * Shape the one JSON object /run sends back.
 *
 * `errorMessage` is already-rendered text (ename/evalue/traceback joined by
 * the caller), never the raw Jupyter-shaped error object - the same
 * narrowing `scripts/positron_run.py`'s `error_text()` does for the same
 * reason: a raw payload is a bigger surface than the one line anyone reading
 * this actually needs.
 */
function summarize({ ok, errorMessage, newImagePaths }) {
  return {
    ok: !!ok,
    status: ok ? 'ok' : 'error',
    error: ok ? null : (errorMessage || 'the console reported the run as failed'),
    new_images: newImagePaths || [],
  };
}

module.exports = {
  isLoopbackAddress,
  checkToken,
  stateFilePath,
  listImages,
  newImages,
  summarize,
  IMAGE_EXT,
};
