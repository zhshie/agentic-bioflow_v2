export const meta = {
  name: 'cloud-burn',
  description: 'cloud-burn v2: run one batch of cloud-burn/tasks.json (code PRs, Opus reviews, mutation runs, reports) for one shard, then land PRs.',
  whenToUse: 'Inside a cloud session on branch cloud/burn-v2, started by the orchestrator prompt in cloud-burn/START.md, once per batch.',
  phases: [
    { title: 'Gate', detail: 'control signal from issue #317 + dynamic HOT scan' },
    { title: 'Build', detail: 'executor per code task in /tmp/cb/<id>, test-first, full suite green' },
    { title: 'Check', detail: 'fresh Opus checker per code task; one fix round on FAIL' },
    { title: 'Land', detail: 'push + open PR via REST (GraphQL is blocked)' },
    { title: 'Review', detail: 'per report task: finders/critic or refuter, markdown to /tmp/cb/reports' },
    { title: 'Scribe', detail: 'one docs branch + one PR for all reports of the batch' },
  ],
}

/*
 * args = {
 *   home: '<absolute path of the cloud/burn-v2 checkout>'   (required; holds cloud-burn/*.sh and RULES.md)
 *   shard: 'A'|'B'|'C', batchNo: 1, batch: [task objects from cloud-burn/tasks.json or generated from its pool],
 *   execModel: 'sonnet', reviewModel: 'opus', helperModel: 'haiku', maxFixRounds: 1,
 *   issue: 317, reportDir: 'docs/reports/cloud-burn-2026-11', utcStart: '<ISO time, from `date -u`>'
 * }
 * Returns { stopped?, results: [{id, kind, status, branch?, pr?, prUrl?, prPayload?, reportPath?, note}] }.
 * The script cannot read files or the clock; agents do. PR creation is attempted by the lander; if the
 * permission layer refuses it inside a subagent, the payload is returned and the main session opens the PR.
 */

const A = args || {}
const HOME = A.home
const SHARD = A.shard || 'A'
const BATCH = A.batch || []
const EXEC = A.execModel || 'sonnet'
const REVIEW = A.reviewModel || 'opus'
const HELPER = A.helperModel || 'haiku'
const FIX_ROUNDS = A.maxFixRounds === undefined ? 1 : A.maxFixRounds
const ISSUE = A.issue || 317
const RDIR = A.reportDir || 'docs/reports/cloud-burn-2026-11'
const R = 'zhshie/agentic-bioflow_v2'
const RULES = `${HOME}/cloud-burn/RULES.md`
const CB = `${HOME}/cloud-burn`

if (!HOME) throw new Error('args.home is required (absolute path of the cloud/burn-v2 checkout)')

const nz = s => typeof s === 'string' && s.trim() !== '' && s.trim() !== '""' && s.trim() !== "''"

const GATE_SCHEMA = { type: 'object', required: ['signal', 'skip', 'hot', 'utc'], properties: {
  signal: { type: 'string', enum: ['GO', 'STOP', 'PAUSE'] }, skip: { type: 'array', items: { type: 'string' } },
  hot: { type: 'array', items: { type: 'string' } }, utc: { type: 'string' },
  remoteBranches: { type: 'array', items: { type: 'string' } }, mergedIds: { type: 'array', items: { type: 'string' } } } }

const EXEC_SCHEMA = { type: 'object', required: ['status', 'head', 'summary'], properties: {
  status: { type: 'string', enum: ['DONE', 'BLOCKED', 'SKIPPED-EXISTS', 'SKIPPED-PREREQ', 'SKIPPED-OVERLAP'] },
  head: { type: 'string' }, summary: { type: 'string' }, runAllTail: { type: 'string' },
  green: { type: 'boolean' }, findings: { type: 'array', items: { type: 'string' } }, filesChanged: { type: 'array', items: { type: 'string' } } } }

const CHECK_SCHEMA = { type: 'object', required: ['verdict', 'reasons'], properties: {
  verdict: { type: 'string', enum: ['PASS', 'FAIL'] }, reasons: { type: 'array', items: { type: 'string' } },
  mustFix: { type: 'array', items: { type: 'string' } } } }

const LAND_SCHEMA = { type: 'object', required: ['pushed'], properties: {
  pushed: { type: 'boolean' }, remoteSha: { type: 'string' }, prNumber: { type: 'number' }, prUrl: { type: 'string' },
  prError: { type: 'string' } } }

const FIND_SCHEMA = { type: 'object', required: ['findings'], properties: { findings: { type: 'array', items: {
  type: 'object', required: ['title', 'severity', 'where', 'evidence'], properties: {
    title: { type: 'string' }, severity: { type: 'string', enum: ['P1', 'P2', 'P3'] }, where: { type: 'string' },
    evidence: { type: 'string' }, repro: { type: 'string' }, fix: { type: 'string' }, redTest: { type: 'string' } } } } } }

const REPORT_SCHEMA = { type: 'object', required: ['path', 'summary'], properties: {
  path: { type: 'string' }, summary: { type: 'string' }, findings: { type: 'number' } } }

const SCRIBE_SCHEMA = { type: 'object', required: ['pushed', 'branch'], properties: {
  pushed: { type: 'boolean' }, branch: { type: 'string' }, prNumber: { type: 'number' }, prUrl: { type: 'string' },
  prError: { type: 'string' }, green: { type: 'boolean' }, files: { type: 'array', items: { type: 'string' } } } }

// ---------- Gate ----------
phase('Gate')
const gate = await agent(
  `Shell helper for cloud-burn. Run exactly, from ${HOME}:\n` +
  `  SHARD=${SHARD} ISSUE=${ISSUE} bash ${CB}/signal.sh\n  ISSUE=${ISSUE} bash ${CB}/hot_scan.sh\n` +
  `  git ls-remote --heads origin | awk '{print $2}' | sed 's#refs/heads/##'\n` +
  `  git log origin/v3 --merges --since=7.days --format=%s | grep -oE 'cb-[a-z0-9]+' | sort -u\n` +
  `Return signal (GO/STOP/PAUSE from signal.sh), skip ids, hot = every line hot_scan.sh printed, utc, ` +
  `remoteBranches = all branch names from ls-remote, mergedIds = the cb-<id> tokens (upper-case the id, e.g. cb-d5 -> D5). ` +
  `Verify each value against the command output; do not invent.`,
  { label: `gate-${SHARD}${A.batchNo || ''}`, schema: GATE_SCHEMA, model: HELPER, effort: 'low' })

if (!gate || gate.signal !== 'GO') {
  log(`signal=${gate ? gate.signal : 'unknown'}; nothing started`)
  return { stopped: gate ? gate.signal : 'GATE-FAILED', results: [] }
}
log(`GO at ${gate.utc}; HOT dynamic ${gate.hot.length} paths; skip [${gate.skip.join(',')}]`)

const HOT = new Set(gate.hot)
const remote = new Set(gate.remoteBranches || [])
const merged = new Set(gate.mergedIds || [])
const intersectsHot = files => (files || []).some(f => HOT.has(f) || [...HOT].some(h => h.endsWith('/') && f.startsWith(h)))

const results = []
const pre = []
const todo = BATCH.filter(t => {
  if (gate.skip.includes(t.id)) { pre.push({ id: t.id, kind: t.kind, status: 'SKIPPED-SIGNAL' }); return false }
  if (t.kind === 'code' && remote.has(t.branch)) { pre.push({ id: t.id, kind: t.kind, status: 'SKIPPED-EXISTS', branch: t.branch }); return false }
  if (t.kind === 'code' && intersectsHot(t.files)) { pre.push({ id: t.id, kind: t.kind, status: 'SKIPPED-OVERLAP' }); return false }
  if (t.id === 'D12' && !merged.has('D5')) { pre.push({ id: t.id, kind: t.kind, status: 'SKIPPED-PREREQ', note: 'D5 not merged' }); return false }
  return true
})
results.push(...pre)
if (pre.length) log(`pre-skipped: ${pre.map(p => `${p.id}:${p.status}`).join(' ')}`)

const codeTasks = todo.filter(t => t.kind === 'code')
const reportTasks = todo.filter(t => t.kind !== 'code')

// ---------- code pipeline ----------
const execPrompt = (t, fix) =>
  `You are the cloud-burn EXECUTOR for task ${t.id}. First read ${RULES} completely and follow §5 exactly ` +
  `(it overrides habits). Repo-relative paths below are relative to the task worktree /tmp/cb/${t.id}.\n` +
  `Task: ${JSON.stringify(t)}\n` +
  `Allowed files (write nothing else except specs/cb-${t.id}/plan.md and ledger.md): ${JSON.stringify(t.files)}\n` +
  (t.prereq ? `Prerequisite (check it first; if unmet return SKIPPED-PREREQ): ${t.prereq}\n` : '') +
  (fix ? `This is a FIX round on the existing worktree /tmp/cb/${t.id} (do not recreate it). The independent checker said:\n${fix}\nFix only that, inside the allowed files, then re-run the full suite.\n`
       : `Create the worktree: git -C ${HOME} fetch origin && git -C ${HOME} worktree add /tmp/cb/${t.id} -b ${t.branch} origin/v3 ` +
         `(if origin already has ${t.branch}: return SKIPPED-EXISTS).\n`) +
  `Environment: python3 -m venv /tmp/cb/venv (once; reuse if present) && /tmp/cb/venv/bin/pip install -q -e /tmp/cb/${t.id}/platform pytest; ` +
  `then rm -rf /tmp/cb/${t.id}/platform/build /tmp/cb/${t.id}/platform/*.egg-info. Run the scope guard before each commit:\n` +
  `  bash ${CB}/check_scope.sh /tmp/cb/${t.id} ${(t.files || []).map(f => `'${f}'`).join(' ')} 'specs/cb-${t.id}/'\n` +
  `Full suite: cd /tmp/cb/${t.id} && PATH=/tmp/cb/venv/bin:$PATH bash tests/run_all.sh (long: run it in the background and wait for it; ` +
  `never two full suites in the same checkout). Commit with explicit paths only. Do NOT push. ` +
  `Return status, head (git rev-parse HEAD), green (true only if run_all's last line says all passed), runAllTail (last 20 lines), ` +
  `filesChanged (git diff --name-only origin/v3...HEAD), findings, summary. Verify every value from command output.`

const checkPrompt = t =>
  `You are an independent cloud-burn CHECKER (fresh context; you did not write this). Read ${RULES} and the repo CLAUDE.md section ` +
  `"For the executor and verifier" (calibration failures included). Task: ${JSON.stringify(t)}\n` +
  `Inspect the worktree /tmp/cb/${t.id}: git -C /tmp/cb/${t.id} log --oneline origin/v3..HEAD; git -C /tmp/cb/${t.id} diff origin/v3...HEAD; ` +
  `read specs/cb-${t.id}/plan.md and ledger.md. Run bash ${CB}/check_scope.sh /tmp/cb/${t.id} ${(t.files || []).map(f => `'${f}'`).join(' ')} 'specs/cb-${t.id}/'. ` +
  `FAIL if any of: scope guard fails; no RED evidence (or mutation proof for pure tests) in the ledger; any existing test deleted, weakened, ` +
  `skipped or xfailed; a baseline grew; behaviour changed where the brief says byte-identical; for gate/regex/credential changes, ` +
  `a shape the base rejected is now accepted (re-run the old shapes on origin/v3 and on HEAD yourself); ledger claims green without the run_all tail; ` +
  `the change does not do what the brief says. Re-run the single new test file(s) yourself. Read-only: change nothing. ` +
  `Return verdict, reasons (file:line), mustFix (concrete).`

const landPrompt = (t, ex) =>
  `Shell helper. In /tmp/cb/${t.id}: confirm git rev-parse HEAD == ${ex.head} and git status --porcelain is empty, then ` +
  `git push origin ${t.branch} (new branch; never --force). Then write /tmp/cb/${t.id}.pr.md with this exact body:\n---\n` +
  prBody(t, ex) + `\n---\nand open the PR via REST: gh api -X POST repos/${R}/pulls -f title='[cloud-burn ${t.id}] ${(t.brief || '').split('.')[0].replace(/'/g, '').slice(0, 70)}' ` +
  `-f head=${t.branch} -f base=v3 -F body=@/tmp/cb/${t.id}.pr.md --jq '.number,.html_url'. Do not use gh pr. If the PR call is refused or errors, ` +
  `return prError with the message (the main session will open it). Return pushed, remoteSha (git ls-remote origin ${t.branch}), prNumber, prUrl. Verify, do not assume.`

function prBody(t, ex) {
  return `Shard ${SHARD} / batch ${A.batchNo || 1} of cloud-burn v2 (tracking #${ISSUE}).\n\n` +
    `**What**: ${ex.summary}\n\n**Files**: ${(ex.filesChanged || []).map(f => '`' + f + '`').join(', ')}\n\n` +
    `**Risk**: ${t.risk || '?'} · **Kind**: ${t.kind}\n\n**RED evidence / ledger**: specs/cb-${t.id}/ledger.md\n\n` +
    `**run_all (cloud VM)**: ${ex.green ? 'green' : 'NOT green locally - see ledger; rely on CI'}\n\n` +
    ((ex.findings || []).length ? `**Findings (not fixed here)**:\n${ex.findings.map(f => '- ' + f).join('\n')}\n\n` : '') +
    `Cloud checker: PASS. Merged only by the local developer-agent after \`VERIFIER: PASS\` and green CI. Do not merge from the cloud.\n\n` +
    `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
}

async function runCode(t) {
  let ex = await agent(execPrompt(t, null), { label: `exec-${t.id}`, phase: 'Build', schema: EXEC_SCHEMA, model: t.model || EXEC, effort: 'high', stallMs: 2400000 })
  if (!ex) return { id: t.id, kind: 'code', status: 'BLOCKED', note: 'executor died' }
  if (ex.status !== 'DONE') return { id: t.id, kind: 'code', status: ex.status, branch: t.branch, note: ex.summary }
  let ck = await agent(checkPrompt(t), { label: `check-${t.id}`, phase: 'Check', schema: CHECK_SCHEMA, model: REVIEW, effort: 'high' })
  let round = 0
  while (ck && ck.verdict === 'FAIL' && round < FIX_ROUNDS) {
    round++
    const fix = (ck.mustFix && ck.mustFix.length ? ck.mustFix : ck.reasons).join('\n')
    ex = await agent(execPrompt(t, fix), { label: `fix${round}-${t.id}`, phase: 'Build', schema: EXEC_SCHEMA, model: t.model || EXEC, effort: 'high', stallMs: 2400000 })
    if (!ex || ex.status !== 'DONE') return { id: t.id, kind: 'code', status: 'BLOCKED', branch: t.branch, note: ex ? ex.summary : 'fix executor died' }
    ck = await agent(checkPrompt(t), { label: `recheck${round}-${t.id}`, phase: 'Check', schema: CHECK_SCHEMA, model: REVIEW, effort: 'high' })
  }
  if (!ck || ck.verdict !== 'PASS') return { id: t.id, kind: 'code', status: 'CHECK-FAIL', branch: t.branch, note: ck ? ck.reasons.join(' | ') : 'checker died' }
  const ld = await agent(landPrompt(t, ex), { label: `land-${t.id}`, phase: 'Land', schema: LAND_SCHEMA, model: HELPER, effort: 'low' })
  const out = { id: t.id, kind: 'code', status: ld && ld.pushed ? (ld.prNumber ? 'PR' : 'PUSHED') : 'PUSH-FAIL', branch: t.branch, green: !!ex.green, note: ex.summary }
  if (ld && ld.prNumber) { out.pr = ld.prNumber; out.prUrl = ld.prUrl }
  else out.prPayload = { title: `[cloud-burn ${t.id}] ${(t.brief || '').split('.')[0].slice(0, 70)}`, head: t.branch, base: 'v3', body: prBody(t, ex), error: ld ? ld.prError : 'lander died' }
  return out
}

// ---------- report pipeline ----------
const reportHead = t =>
  `Read ${RULES} §2, §3 and §6 first. You write NO repository file; your only output file is /tmp/cb/reports/${t.id}.md ` +
  `(mkdir -p /tmp/cb/reports). Work read-only against a scratch checkout: git -C ${HOME} worktree add --detach /tmp/cb/ro-${t.id} origin/v3 ` +
  `(reuse if present). Put the origin/v3 sha on the first line of the report. Task: ${JSON.stringify(t)}\n`

const LENSES = [
  ['correctness', 'logic errors, wrong branches, off-by-one, unhandled None/empty, wrong return on error paths, broken invariants stated in docstrings or the constitution'],
  ['safety-gates', 'every input/path/credential/permission/confirmation gate: find inputs the gate lets through that it should stop (fail-open), injection, path traversal, secrets in logs or URLs'],
  ['contract-drift', 'what docs (docs/*.md, specs/*/spec.md, docstrings, MCP tool descriptions, CLI help) promise vs what the code does; untested promises; dead code'],
]

async function runReview(t) {
  const unit = (t.unit || []).join(', ')
  const finds = await parallel(LENSES.map(([lens, what]) => () => agent(
    reportHead(t) + `Adversarial reviewer, lens "${lens}": ${what}. Unit under review: ${unit}. Read the unit fully, its callers and its tests ` +
    `(git grep). Report only findings with concrete evidence (file:line at origin/v3 and why). Prefer proving with a tiny python3 -I or bash snippet run ` +
    `in /tmp (never edit the checkout). Do not write the report file; just return findings.`,
    { label: `find-${t.id}-${lens}`, phase: 'Review', schema: FIND_SCHEMA, model: REVIEW, effort: 'high' })))
  const all = finds.filter(Boolean).flatMap(f => f.findings)
  const rep = await agent(
    reportHead(t) + `You are the REFUTER and author. Below are ${all.length} candidate findings from three independent reviewers of ${unit}. ` +
    `For each: try hard to refute it (read the code, run a snippet; default to refuted if the evidence does not hold). Merge duplicates. ` +
    `Then write /tmp/cb/reports/${t.id}.md: title "${t.id} adversarial review: ${unit}", sha line, scope, method (3 lenses + refutation), ` +
    `surviving findings sorted by severity in the RULES §6 format, then "Refuted" with reasons, then "Suggested follow-up tasks" (each with tier and whether it is HOT). ` +
    `Candidates:\n${JSON.stringify(all)}\nReturn path, summary (one paragraph), findings (count surviving).`,
    { label: `refute-${t.id}`, phase: 'Review', schema: REPORT_SCHEMA, model: REVIEW, effort: 'xhigh' })
  return rep
}

async function runMutation(t) {
  return agent(
    `Read ${RULES} §2, §3 and §6. Mutation-testing run for ${(t.unit || []).join(', ')} (task ${JSON.stringify(t)}). ` +
    `Make a private copy: git -C ${HOME} worktree add --detach /tmp/cb/mu-${t.id} origin/v3 (reuse if present); venv /tmp/cb/venv as in RULES §5. ` +
    `Find the tests that exercise the unit (git grep the module/function names under platform/tests and tests/). Create at least 15 mutants, ` +
    `one at a time, each a single small semantic change (flip a comparison, drop a branch, change a constant, return early, swap and/or, ` +
    `remove a gate check). For each: apply, run ONLY the relevant test files (timeout 10 min), record killed/survived and the killing test, ` +
    `then git -C /tmp/cb/mu-${t.id} checkout -- . (verify clean). Never commit, never push. You may try pip install mutmut for extra coverage; ` +
    `note if it fails. Write /tmp/cb/reports/${t.id}.md: sha line, unit, test files used, table of mutants (file:line, change, killed by / SURVIVED), ` +
    `mutation score, and for every survivor a proposed RED test (name + assertion) and whether the unit is HOT. Return path, summary, findings (survivors count).`,
    { label: `mutate-${t.id}`, phase: 'Review', schema: REPORT_SCHEMA, model: t.model || EXEC, effort: 'high', stallMs: 2400000 })
}

async function runPlainReport(t) {
  const draft = await agent(
    reportHead(t) + `Do the task's brief end to end (install what you need from pypi/npm into /tmp; Chrome for Testing is at $CHROME_PATH). ` +
    `Write /tmp/cb/reports/${t.id}.md. Return path, summary, findings.`,
    { label: `draft-${t.id}`, phase: 'Review', schema: REPORT_SCHEMA, model: t.model || REVIEW, effort: 'high', stallMs: 2400000 })
  if (!draft) return null
  return agent(
    reportHead(t) + `You are the COMPLETENESS CRITIC for /tmp/cb/reports/${t.id}.md (written by another agent). Check: does it cover the whole brief? ` +
    `Pick at least 8 of its factual claims (file:line, counts, command outputs) and verify each yourself against origin/v3; fix or strike wrong ones ` +
    `(list struck claims in a "Corrections by critic" section). Add anything clearly missing. Edit the file in place. Return path, summary, findings.`,
    { label: `critic-${t.id}`, phase: 'Review', schema: REPORT_SCHEMA, model: REVIEW, effort: 'high' })
}

async function runReport(t) {
  let r = null
  if (t.kind === 'review') r = await runReview(t)
  else if (t.kind === 'mutation') r = await runMutation(t)
  else r = await runPlainReport(t)
  return r && nz(r.path) ? { id: t.id, kind: t.kind, status: 'REPORTED', reportPath: r.path, note: r.summary, findings: r.findings }
                        : { id: t.id, kind: t.kind, status: 'BLOCKED', note: 'no report produced' }
}

const [codeRes, repRes] = await parallel([
  () => pipeline(codeTasks, t => runCode(t)),
  () => pipeline(reportTasks, t => runReport(t)),
])
results.push(...(codeRes || []).filter(Boolean), ...(repRes || []).filter(Boolean))

// ---------- Scribe ----------
const reported = results.filter(r => r.status === 'REPORTED')
if (reported.length) {
  phase('Scribe')
  const branch = `docs/cb-reports-${SHARD.toLowerCase()}-${A.batchNo || 1}`
  const list = reported.map(r => `/tmp/cb/reports/${r.id}.md -> ${RDIR}/${r.id}.md`).join('\n')
  const sc = await agent(
    `Read ${RULES} §2 and §5. Scribe for shard ${SHARD} batch ${A.batchNo || 1}. If origin already has ${branch}, use ${branch}-b (then -c...). ` +
    `git -C ${HOME} fetch origin && git -C ${HOME} worktree add /tmp/cb/scribe-${SHARD}${A.batchNo || 1} -b <branch> origin/v3. Copy these files verbatim:\n${list}\n` +
    `Also write ${RDIR}/README.md if it does not exist on origin/v3 (one line per report: id, title, one-sentence summary) or append the new lines if it exists in this branch. ` +
    `Scope guard: bash ${CB}/check_scope.sh <worktree> '${RDIR}/'. Full suite once: PATH=/tmp/cb/venv/bin:$PATH bash tests/run_all.sh (create the venv per RULES §5 if missing). ` +
    `If a test fails because of the new files (e.g. a docs lint), fix the report files only; if it fails for an unrelated reason, note it. Commit explicit paths ` +
    `"docs(reports): cloud-burn ${SHARD}${A.batchNo || 1} - ${reported.map(r => r.id).join(', ')}", git push origin <branch>, then open a PR via ` +
    `gh api -X POST repos/${R}/pulls -f title='[cloud-burn reports ${SHARD}${A.batchNo || 1}] ${reported.map(r => r.id).join(' ')}' -f head=<branch> -f base=v3 -F body=@<file> ` +
    `where the body lists each report with its summary and surviving-finding count, says "reports only, no code; merge by the local developer-agent", links #${ISSUE}, ` +
    `and ends with the line 🤖 Generated with [Claude Code](https://claude.com/claude-code). Never use gh pr. Return pushed, branch, prNumber, prUrl or prError, green, files.`,
    { label: `scribe-${SHARD}${A.batchNo || 1}`, phase: 'Scribe', schema: SCRIBE_SCHEMA, model: EXEC, effort: 'medium' })
  results.push({ id: `reports-${SHARD}${A.batchNo || 1}`, kind: 'scribe', status: sc && sc.pushed ? (sc.prNumber ? 'PR' : 'PUSHED') : 'PUSH-FAIL',
    branch: sc ? sc.branch : branch, pr: sc ? sc.prNumber : undefined, prUrl: sc ? sc.prUrl : undefined, note: sc ? (sc.prError || '') : 'scribe died', green: sc ? sc.green : false })
}

log(results.map(r => `${r.id}:${r.status}${r.pr ? '#' + r.pr : ''}`).join(' '))
return { stopped: null, gateUtc: gate.utc, results }
