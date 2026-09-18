/*---------------------------------------------------------------------------------------------
 * Trimmed, vendored copy. Not an npm package: Positron does not publish
 * `positron.d.ts` to the npm registry the way VS Code publishes `@types/vscode`
 * - it ships only inside the Positron source tree
 * (`src/positron-dts/positron.d.ts` in posit-dev/positron), where an
 * extension that runs *inside* Positron gets it for free at build time.
 * A standalone extension repo like this one has no such build step, so this
 * file copies just the members positron-bridge actually calls, fetched from
 * posit-dev/positron @ main on 2026-09-18 (the `runtime.executeCode` family,
 * unchanged in shape since it was first documented - see
 * scripts/positron_run.py's own header for the same API named from outside).
 *
 * If Positron ever changes this signature, the fix is re-fetching the
 * relevant section from that file, not guessing - the same "measure before
 * claiming" rule as everywhere else in this repo (docs/PRINCIPLES.md,
 * invariant 8).
 *--------------------------------------------------------------------------------------------*/

declare module 'positron' {

	import * as vscode from 'vscode';

	/** The current Positron version, e.g. "2026.04.0". */
	export const version: string;

	/** Possible code execution modes for a language runtime. */
	export enum RuntimeCodeExecutionMode {
		Interactive = 'interactive',
		NonInteractive = 'non-interactive',
		Transient = 'transient',
		Silent = 'silent',
		Unprocessed = 'unprocessed',
	}

	/** Possible error dispositions for a language runtime. */
	export enum RuntimeErrorBehavior {
		Stop = 'stop',
		Continue = 'continue',
	}

	namespace runtime {
		/**
		 * An object that observes an ongoing code execution invoked from the
		 * `executeCode` API. Only the fields positron-bridge reads are kept
		 * here; the full interface also carries onOutput/onPlot/onData, which
		 * this bridge deliberately does not use - see extension.ts for why.
		 */
		export interface ExecutionObserver {
			token?: vscode.CancellationToken;
			onStarted?: () => void;
			onOutput?: (message: string) => void;
			onError?: (message: string) => void;
			/** One of onCompleted or onFailed fires, never both. */
			onCompleted?: (result: Record<string, any>) => void;
			/** One of onCompleted or onFailed fires, never both. */
			onFailed?: (error: Error) => void;
			/** Fires last, whichever of the two above fired. */
			onFinished?: () => void;
		}

		/**
		 * Executes code in a language runtime's console, as though it were
		 * typed interactively by the user. Full parameter docs live in the
		 * upstream file cited above; positron-bridge only ever passes
		 * languageId, code, focus, and observer.
		 */
		export function executeCode(
			languageId: string,
			code: string,
			focus: boolean,
			allowIncomplete?: boolean,
			mode?: RuntimeCodeExecutionMode,
			errorBehavior?: RuntimeErrorBehavior,
			observer?: ExecutionObserver,
			sessionId?: string,
			documentUri?: vscode.Uri,
			executionMetadata?: Record<string, any>,
			attributionMetadata?: Record<string, any>
		): Thenable<Record<string, any>>;
	}
}
