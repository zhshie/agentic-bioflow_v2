'use strict';
// Tests for src/bridge-core.js - the half of positron-bridge that runs
// outside Positron. No `vscode`/`positron` import anywhere in this file on
// purpose: those modules only exist inside a running Positron window, and
// standing one up is not something this repo's test suite can do (the same
// limit noted in bridge-core.js's own header). extension.ts's HTTP/executeCode
// wiring is therefore exercised by hand against a real Positron, not here -
// what *is* here is every decision that does not require one: the loopback
// check, the token check, the three state-file paths, and the image diff.
//
// Plain node, no test framework: this repo's other tests are bash scripts
// that print ok/FAIL per case and signal the verdict with their exit code
// (tests/run_all.sh's own convention); this file matches that shape instead
// of a framework runner tests/positron_bridge_test.sh would then have to
// install.
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const core = require('../src/bridge-core.js');

let fails = 0;
function t(label, fn) {
  try {
    fn();
    console.log('ok    ' + label);
  } catch (err) {
    fails += 1;
    console.log('FAIL  ' + label + '  -- ' + (err && err.message ? err.message : err));
  }
}

// --------------------------------------------------------------------------
// isLoopbackAddress
// --------------------------------------------------------------------------
t('127.0.0.1 is loopback', () => assert.strictEqual(core.isLoopbackAddress('127.0.0.1'), true));
t('127.9.9.9 (whole 127/8) is loopback', () => assert.strictEqual(core.isLoopbackAddress('127.9.9.9'), true));
t('::1 is loopback', () => assert.strictEqual(core.isLoopbackAddress('::1'), true));
t('IPv4-mapped ::ffff:127.0.0.1 is loopback', () =>
  assert.strictEqual(core.isLoopbackAddress('::ffff:127.0.0.1'), true));
t('a LAN address is not loopback', () => assert.strictEqual(core.isLoopbackAddress('192.168.1.5'), false));
t('a public address is not loopback', () => assert.strictEqual(core.isLoopbackAddress('8.8.8.8'), false));
t('undefined is not loopback', () => assert.strictEqual(core.isLoopbackAddress(undefined), false));
t('empty string is not loopback', () => assert.strictEqual(core.isLoopbackAddress(''), false));

// --------------------------------------------------------------------------
// checkToken
// --------------------------------------------------------------------------
const TOKEN = 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6';
t('correct bearer token is accepted', () => assert.strictEqual(core.checkToken(`Bearer ${TOKEN}`, TOKEN), true));
t('wrong token is rejected', () => assert.strictEqual(core.checkToken('Bearer nope', TOKEN), false));
t('missing header is rejected', () => assert.strictEqual(core.checkToken(undefined, TOKEN), false));
t('header without Bearer prefix is rejected', () => assert.strictEqual(core.checkToken(TOKEN, TOKEN), false));
t('a shorter guess is rejected, not thrown', () => assert.strictEqual(core.checkToken('Bearer a1b2', TOKEN), false));
t('a longer guess is rejected, not thrown', () =>
  assert.strictEqual(core.checkToken(`Bearer ${TOKEN}extra`, TOKEN), false));
t('empty configured token never matches', () => assert.strictEqual(core.checkToken(`Bearer ${TOKEN}`, ''), false));
t('non-string header is rejected, not thrown', () => assert.strictEqual(core.checkToken(42, TOKEN), false));

// --------------------------------------------------------------------------
// stateFilePath - the three OS cases the card asks for
// --------------------------------------------------------------------------
t('linux: honours XDG_STATE_HOME', () => {
  const p = core.stateFilePath({ XDG_STATE_HOME: '/home/u/.state' }, 'linux');
  assert.strictEqual(p, path.join('/home/u/.state', 'agentic-bioflow', 'positron-bridge.json'));
});
t('linux: falls back to ~/.local/state with no XDG var set', () => {
  const p = core.stateFilePath({ HOME: '/home/u' }, 'linux');
  assert.strictEqual(p, path.join('/home/u', '.local', 'state', 'agentic-bioflow', 'positron-bridge.json'));
});
t('macos: same XDG convention as linux (no Mac-native equivalent exists)', () => {
  const p = core.stateFilePath({ HOME: '/Users/u' }, 'darwin');
  assert.strictEqual(p, path.join('/Users/u', '.local', 'state', 'agentic-bioflow', 'positron-bridge.json'));
});
t('windows: uses %LOCALAPPDATA%', () => {
  const p = core.stateFilePath({ LOCALAPPDATA: 'C:\\Users\\u\\AppData\\Local' }, 'win32');
  assert.strictEqual(p, path.join('C:\\Users\\u\\AppData\\Local', 'agentic-bioflow', 'positron-bridge.json'));
});
t('windows: falls back to %USERPROFILE%\\AppData\\Local with no LOCALAPPDATA', () => {
  const p = core.stateFilePath({ USERPROFILE: 'C:\\Users\\u' }, 'win32');
  assert.strictEqual(
    p,
    path.join(path.join('C:\\Users\\u', 'AppData', 'Local'), 'agentic-bioflow', 'positron-bridge.json')
  );
});
t('never lands under a project folder path shape', () => {
  // Regression guard for the one rule that actually matters here: whatever
  // the OS branch, nothing about the *value* of a project-folder-shaped env
  // var (PWD, INIT_CWD) can influence the answer.
  const p = core.stateFilePath({ HOME: '/home/u', PWD: '/home/u/Documents/project' }, 'linux');
  assert.ok(!p.includes('Documents'));
});

// --------------------------------------------------------------------------
// listImages / newImages
// --------------------------------------------------------------------------
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'positron-bridge-test-'));
try {
  t('listImages finds image files by extension, ignores others', () => {
    fs.writeFileSync(path.join(tmp, 'plot.png'), 'x');
    fs.writeFileSync(path.join(tmp, 'notes.txt'), 'x');
    fs.mkdirSync(path.join(tmp, 'sub'));
    fs.writeFileSync(path.join(tmp, 'sub', 'fig.pdf'), 'x');
    const found = core.listImages(tmp);
    const names = [...found.keys()].map((p) => path.relative(tmp, p)).sort();
    assert.deepStrictEqual(names, ['plot.png', path.join('sub', 'fig.pdf')]);
  });

  t('listImages skips dotfiles/dot-directories', () => {
    fs.mkdirSync(path.join(tmp, '.git'), { recursive: true });
    fs.writeFileSync(path.join(tmp, '.git', 'hidden.png'), 'x');
    fs.writeFileSync(path.join(tmp, '.hidden.png'), 'x');
    const found = core.listImages(tmp);
    const names = [...found.keys()].map((p) => path.basename(p));
    assert.ok(!names.includes('hidden.png'));
    assert.ok(!names.includes('.hidden.png'));
  });

  t('listImages on a missing/undefined dir returns empty, does not throw', () => {
    assert.strictEqual(core.listImages(undefined).size, 0);
    assert.strictEqual(core.listImages(path.join(tmp, 'does-not-exist')).size, 0);
  });

  t('newImages reports a file absent from the before snapshot', () => {
    const before = core.listImages(tmp);
    const freshDir = fs.mkdtempSync(path.join(os.tmpdir(), 'positron-bridge-new-'));
    fs.writeFileSync(path.join(freshDir, 'result.png'), 'x');
    const after = new Map(before);
    const stat = fs.statSync(path.join(freshDir, 'result.png'));
    after.set(path.join(freshDir, 'result.png'), stat.mtimeMs);
    const diff = core.newImages(before, after);
    assert.ok(diff.includes(path.join(freshDir, 'result.png')));
    fs.rmSync(freshDir, { recursive: true, force: true });
  });

  t('newImages reports a file overwritten in place (later mtime), not just new paths', () => {
    const file = path.join(tmp, 'plot.png');
    const before = new Map([[file, 1000]]);
    const after = new Map([[file, 2000]]);
    assert.deepStrictEqual(core.newImages(before, after), [file]);
  });

  t('newImages reports nothing when mtimes are unchanged', () => {
    const file = path.join(tmp, 'plot.png');
    const before = new Map([[file, 1000]]);
    const after = new Map([[file, 1000]]);
    assert.deepStrictEqual(core.newImages(before, after), []);
  });
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}

// --------------------------------------------------------------------------
// summarize - the exact reply shape /run sends
// --------------------------------------------------------------------------
t('summarize: success carries no error and the image list', () => {
  const out = core.summarize({ ok: true, newImagePaths: ['figs/a.png'] });
  assert.deepStrictEqual(out, { ok: true, status: 'ok', error: null, new_images: ['figs/a.png'] });
});
t('summarize: failure carries the given message', () => {
  const out = core.summarize({ ok: false, errorMessage: 'Error: boom', newImagePaths: [] });
  assert.deepStrictEqual(out, { ok: false, status: 'error', error: 'Error: boom', new_images: [] });
});
t('summarize: failure with no message still explains itself', () => {
  const out = core.summarize({ ok: false, newImagePaths: [] });
  assert.strictEqual(typeof out.error, 'string');
  assert.ok(out.error.length > 0);
});
t('summarize never carries a raw stdout/stderr field', () => {
  // Regression guard for the card's own requirement: the full console
  // transcript must never be part of what /run returns.
  const out = core.summarize({ ok: true, newImagePaths: [] });
  assert.ok(!('stdout' in out));
  assert.ok(!('stderr' in out));
  assert.ok(!('output' in out));
});

console.log('');
if (fails > 0) {
  console.log(`FAIL: ${fails} case(s)`);
  process.exit(1);
}
console.log('OK: positron-bridge bridge-core.js');
