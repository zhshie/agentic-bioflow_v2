// positron-bridge: the extension GitHub issue #14 asks for.
//
// Why this exists at all - the short version, the long version is
// scripts/positron_run.py's own header and docs/PITFALLS.md's kallichore
// entry: kallichore 0.1.68 stopped writing `kallichore-*.json` connection
// files and now hands connection info to Positron's own main process over a
// one-shot handshake named pipe that is consumed before any external process
// could read it. `positron.runtime.executeCode` still exists and still
// works - but it is only callable from inside an extension, which is the
// one thing nothing in this repo previously shipped. This file is that
// extension: the whole of it.
//
// Everything that does not need the vscode/positron API lives in
// bridge-core.js instead, so it can be tested with plain `node` - see that
// file's own header for why.
import * as vscode from 'vscode';
import * as positron from 'positron';
import * as http from 'http';
import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';
import type { AddressInfo } from 'net';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const core = require('./bridge-core.js') as typeof import('./bridge-core');

const MAX_BODY_BYTES = 10 * 1024 * 1024; // a code snippet, not a data upload

let server: http.Server | undefined;
let statePath: string | undefined;

export function activate(context: vscode.ExtensionContext): void {
	// A fresh token every activation - never reused across restarts, and
	// never derived from anything guessable (PID, timestamp). Whoever holds
	// the current state file holds the current token; there is no other way
	// in.
	const token = crypto.randomBytes(24).toString('hex');
	const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

	server = http.createServer((req, res) => handleRequest(req, res, token, workspaceRoot));

	// 127.0.0.1, not '0.0.0.0' or the unspecified address: binding loopback
	// only is the first of two independent defenses (the second is the
	// per-request remoteAddress check in handleRequest, for the platforms
	// where "bound to 127.0.0.1" and "reachable only from this machine" can
	// still drift apart under a misconfigured host firewall/NAT).
	// Port 0 asks the OS for whatever is free, so two members on one shared
	// dev box, or two Positron windows on one desktop, never collide the way
	// a fixed port would.
	server.listen(0, '127.0.0.1', () => {
		const { port } = server!.address() as AddressInfo;
		statePath = core.stateFilePath(process.env, process.platform);
		try {
			fs.mkdirSync(path.dirname(statePath), { recursive: true });
			const payload = JSON.stringify({
				port,
				token,
				positron_version: positron.version,
				pid: process.pid,
			});
			// Written private and only after the server is already listening,
			// so nothing can read a port/token pair for a server that is not
			// yet accepting connections. 0o600: same posture as the
			// deployment settings file this repo already writes privately
			// (docs/SETTINGS.md) - a bearer token is a credential like any
			// other.
			fs.writeFileSync(statePath, payload, { mode: 0o600 });
		} catch (err) {
			// Not writing the file is a real failure - nothing outside this
			// window can find the bridge - but it must not crash Positron
			// itself. Surface it where a person will see it.
			vscode.window.showErrorMessage(
				`agentic-bioflow positron-bridge: could not write its state file (${(err as Error).message}). ` +
					'The bridge is running but nothing can discover it.'
			);
		}
	});

	context.subscriptions.push({ dispose: () => teardown() });
}

export function deactivate(): void {
	teardown();
}

function teardown(): void {
	// The file is the only thing an external caller can see; removing it is
	// what makes "no bridge" true again the moment this window stops being
	// able to answer for it. A stale file pointing at a dead port is exactly
	// the kallichore-file failure mode this extension exists to avoid
	// reintroducing.
	if (statePath) {
		try {
			fs.unlinkSync(statePath);
		} catch {
			// already gone, or never got written - either way, nothing to undo
		}
		statePath = undefined;
	}
	if (server) {
		server.close();
		server = undefined;
	}
}

function handleRequest(
	req: http.IncomingMessage,
	res: http.ServerResponse,
	token: string,
	workspaceRoot: string | undefined
): void {
	// Loopback check first, before the token is even inspected: a
	// non-loopback caller gets the same 403 whether or not it also guessed
	// the token, so the token check never runs against network input.
	if (!core.isLoopbackAddress(req.socket.remoteAddress)) {
		res.writeHead(403, { 'Content-Type': 'application/json' }).end(
			JSON.stringify({ ok: false, error: 'loopback connections only' })
		);
		return;
	}
	if (req.method !== 'POST' || req.url !== '/run') {
		res.writeHead(404, { 'Content-Type': 'application/json' }).end(
			JSON.stringify({ ok: false, error: 'POST /run is the only endpoint' })
		);
		return;
	}
	if (!core.checkToken(req.headers['authorization'], token)) {
		res.writeHead(401, { 'Content-Type': 'application/json' }).end(
			JSON.stringify({ ok: false, error: 'bad or missing token' })
		);
		return;
	}

	const chunks: Buffer[] = [];
	let size = 0;
	let tooBig = false;
	req.on('data', (chunk: Buffer) => {
		size += chunk.length;
		if (size > MAX_BODY_BYTES) {
			tooBig = true;
			req.destroy();
			return;
		}
		chunks.push(chunk);
	});
	req.on('end', () => {
		if (tooBig) return; // response already impossible; connection is gone
		void runOne(Buffer.concat(chunks).toString('utf8'), res, workspaceRoot);
	});
	req.on('error', () => {
		try {
			res.writeHead(400).end();
		} catch {
			/* connection already gone */
		}
	});
}

async function runOne(
	rawBody: string,
	res: http.ServerResponse,
	workspaceRoot: string | undefined
): Promise<void> {
	let lang: string;
	let code: string;
	try {
		const body = JSON.parse(rawBody);
		if (typeof body.code !== 'string' || !body.code) throw new Error('code must be a non-empty string');
		if (typeof body.lang !== 'string') throw new Error('lang must be a string');
		lang = body.lang.toLowerCase();
		code = body.code;
	} catch (err) {
		res.writeHead(400, { 'Content-Type': 'application/json' }).end(
			JSON.stringify({ ok: false, error: `bad request body: ${(err as Error).message}` })
		);
		return;
	}
	// Positron's own language IDs, lowercase - the same two this plugin
	// already names in scripts/positron_run.py's LANGUAGES table, spelled
	// the way executeCode expects rather than the way a session lists its
	// display language.
	if (lang !== 'r' && lang !== 'python') {
		res.writeHead(400, { 'Content-Type': 'application/json' }).end(
			JSON.stringify({ ok: false, error: `unsupported lang ${JSON.stringify(lang)}: only "r" or "python"` })
		);
		return;
	}

	const before = core.listImages(workspaceRoot);
	const result = await execute(lang, code);
	const after = core.listImages(workspaceRoot);
	const newImagePaths = core.newImages(before, after).map((p) =>
		workspaceRoot ? path.relative(workspaceRoot, p) : p
	);

	res.writeHead(200, { 'Content-Type': 'application/json' }).end(
		JSON.stringify(core.summarize({ ok: result.ok, errorMessage: result.errorMessage, newImagePaths }))
	);
}

/**
 * Run one snippet and reduce whatever Positron reports to ok/errorMessage.
 *
 * `NonInteractive`: shown to the caller's console (so a human looking at
 * Positron sees the same run a person watching over their shoulder would),
 * not merged with whatever the person themselves is mid-typing, and kept in
 * history - the same three properties `positron_run.py` gets from
 * `source(..., echo = TRUE)` for the same reason. `onOutput`/`onError` are
 * deliberately not wired up: the full stream is what this endpoint exists to
 * avoid shipping back over HTTP (see this file's own top comment and the
 * card's own text) - it stays on Positron's own console for a person to read
 * there.
 */
function execute(languageId: 'r' | 'python', code: string): Promise<{ ok: boolean; errorMessage?: string }> {
	return new Promise((resolve) => {
		let settled = false;
		const finish = (ok: boolean, errorMessage?: string) => {
			if (settled) return;
			settled = true;
			resolve({ ok, errorMessage });
		};
		positron.runtime
			.executeCode(
				languageId,
				code,
				false, // focus: do not steal window focus for an agent-issued run
				false, // allowIncomplete: a syntactically incomplete snippet is a real error, not something to guess at
				positron.RuntimeCodeExecutionMode.NonInteractive,
				positron.RuntimeErrorBehavior.Stop,
				{
					onFailed: (error: Error) => finish(false, error.message),
					onCompleted: () => finish(true),
					// onFinished is the backstop: onCompleted/onFailed are documented
					// as mutually exclusive, but if a future Positron build fires
					// neither, this still resolves instead of hanging the HTTP
					// response forever.
					onFinished: () => finish(true),
				}
			)
			.then(undefined, (err: unknown) => finish(false, err instanceof Error ? err.message : String(err)));
	});
}
