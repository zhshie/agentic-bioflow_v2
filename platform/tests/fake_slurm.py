# Nothing existing: no maintained tool fakes sbatch, squeue and sacct as PATH scripts for offline tests; the output shapes are the ones this repo parses.
"""A fake Slurm (sbatch, squeue, sacct) for tests, written into a temp folder and put first on PATH.

SU rate: UNCONFIRMED. "1 SU = 1 core-hour" is inferred, not stated by NCHC (configs/sites/su_rates.json, key assumption).
Nothing here carries a rate; a test that turns SU into money reads the one rates file.

What this proves and what it does not: the fake commands prove only OUR parsing of the text we expect. They do not prove what a
real Slurm does (docs/PITFALLS.md item 42: the real behaviour is not verified). Nothing here claims any verification against a real scheduler.
The column order JobID|State|ExitCode|Elapsed|AllocCPUS|Partition is an assumption (欄位順序為假設，未經 nano4 實測);
the real `sacct -P` output is on the nano4 acceptance to-do list. Column names are only those PITFALLS already shows:
JobID, State, ExitCode, Elapsed, AllocCPUS, Partition.

The scripts are POSIX sh, never eval their input, write only under the state folder in ABF_FAKE_SLURM_DIR, and without that
variable refuse with rc 99 ("fake slurm: not configured") so they cannot be mistaken for a real Slurm.
"""
import os
import stat
import subprocess

COLUMNS = ("JobID", "State", "ExitCode", "Elapsed", "AllocCPUS", "Partition")
DEFAULT_JOB = 4242

# state -> ExitCode as sacct would print it (an assumption, not measured on nano4)
STATES = {
    "COMPLETED": "0:0",
    "FAILED": "1:0",
    "TIMEOUT": "0:0",
    "OUT_OF_MEMORY": "0:125",
    "NODE_FAIL": "1:0",
    "CANCELLED": "0:15",
}
CANCELLED_BY = "CANCELLED by 1234"      # sacct appends "by <uid>" when a user cancelled the job
# docs/PITFALLS.md (~665): a task that failed before it started leaves only a bare exit 1, no trace, so no realtime.
FAILED_NO_TRACE = {"state": "FAILED", "exit_code": "1:0", "trace": False, "note": "bare exit 1, Nextflow got no trace"}

_COMMON = r'''#!/bin/sh
D="${ABF_FAKE_SLURM_DIR:-}"
if [ -z "$D" ]; then echo "fake slurm: not configured" >&2; exit 99; fi
echo "$PROG $*" >> "$D/calls.log"
JOB=""; XFLAG=0; OUT=""; prev=""
for a in "$@"; do
  case "$prev" in -j) JOB="$a" ;; -o) OUT="$a" ;; esac
  [ "$a" = "-X" ] && XFLAG=1
  prev="$a"
done
case "$PROG" in sacct|squeue)
  if [ -n "$JOB" ]; then
    case "$JOB" in *[!0-9]*) echo "fake slurm: bad job id" >&2; exit 2 ;; esac
  fi ;;
esac
'''

_SBATCH = r'''
if [ -e "$D/fail_sbatch" ]; then echo "sbatch: error: fake failure" >&2; exit 1; fi
ID=%d
[ -f "$D/sbatch_id" ] && read ID < "$D/sbatch_id"
echo "Submitted batch job $ID"
'''

_SQUEUE = r'''
if [ -e "$D/invalid_squeue" ]; then echo "slurm_load_jobs error: Invalid job id specified" >&2; exit 1; fi
if [ -f "$D/alive_$JOB" ]; then read S < "$D/alive_$JOB"; echo "$S"; else echo ""; fi
exit 0
'''

_SACCT = r'''
if [ -e "$D/fail_sacct" ]; then echo "sacct: error: fake failure" >&2; exit 1; fi
[ -f "$D/rows_$JOB" ] || exit 0
first=1
while IFS='|' read -r c1 c2 c3 c4 c5 c6; do
  if [ "$XFLAG" = 1 ] && [ "$first" = 0 ]; then break; fi
  first=0
  case "$OUT" in State) echo "$c2" ;; *) echo "$c1|$c2|$c3|$c4|$c5|$c6" ;; esac
done < "$D/rows_$JOB"
'''


def sacct_rows(job_id, state, elapsed="01:00:00", ncpus=4, partition="ct56", steps=True, exit_code=None, step_states=None):
    """`sacct -n -P` text: JobID|State|ExitCode|Elapsed|AllocCPUS|Partition, one line per row, no header.
    steps=True adds <id>.batch and <id>.extern rows; their State may differ from the main row (NODE_FAIL main, CANCELLED .batch)."""
    base = state.split()[0]
    if exit_code is None:
        exit_code = STATES[base]
    if step_states is None:
        step_states = ("CANCELLED" if base == "NODE_FAIL" else base, "COMPLETED")
    rows = [(str(job_id), state, exit_code, elapsed, ncpus, partition)]
    if steps:
        rows.append(("%s.batch" % job_id, step_states[0], exit_code, elapsed, ncpus, ""))
        rows.append(("%s.extern" % job_id, step_states[1], "0:0", elapsed, ncpus, ""))
    return "".join("|".join(str(c) for c in r) + "\n" for r in rows)


class FakeSlurm:
    def __init__(self, root):
        self.bin = root / "fakeslurm-bin"
        self.state = root / "fakeslurm-state"

    @property
    def calls_file(self):
        return self.state / "calls.log"

    def calls(self):
        """Every call the fake scripts saw, one `<prog> <args>` per line."""
        return self.calls_file.read_text().splitlines() if self.calls_file.exists() else []

    def set(self, job_id, state_or_none, source="sacct", **kw):
        """Make job_id show `state_or_none` in `source` ("sacct" rows, or "squeue" for a live PENDING/RUNNING job).
        None removes it from that source (an empty sacct answer, or a job squeue no longer lists)."""
        if source == "sacct":
            f = self.state / ("rows_%s" % job_id)
            if state_or_none is None:
                f.unlink(missing_ok=True)
            else:
                f.write_text(sacct_rows(job_id, state_or_none, **kw))
        elif source == "squeue":
            f = self.state / ("alive_%s" % job_id)
            if state_or_none is None:
                f.unlink(missing_ok=True)
            else:
                f.write_text(state_or_none + "\n")
        else:
            raise ValueError("source must be sacct or squeue")

    def flag(self, name, on=True):
        """Switch a failure on or off: fail_sacct, fail_sbatch, invalid_squeue."""
        f = self.state / name
        if on:
            f.write_text("")
        else:
            f.unlink(missing_ok=True)

    def path(self, prog):
        return str(self.bin / prog)

    def run(self, prog, *args, env=None):
        """Run the fake script of `prog` (by its full path in the temp folder, never a PATH lookup)."""
        e = dict(os.environ) if env is None else env
        return subprocess.run([self.path(prog)] + list(args), capture_output=True, text=True, env=e)


def install(tmp_path, monkeypatch, *, jobs=None):
    """Write the three fake commands under tmp_path, put them first on PATH and point ABF_FAKE_SLURM_DIR at the state folder.
    jobs: {job_id: sacct state name or None}; everything is undone by monkeypatch."""
    fs = FakeSlurm(tmp_path)
    fs.bin.mkdir()
    fs.state.mkdir()
    for prog, body in (("sbatch", _SBATCH % DEFAULT_JOB), ("squeue", _SQUEUE), ("sacct", _SACCT)):
        script = _COMMON.replace('#!/bin/sh\n', '#!/bin/sh\nPROG=%s\n' % prog, 1) + body
        p = fs.bin / prog
        p.write_text(script)
        p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("PATH", str(fs.bin) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("ABF_FAKE_SLURM_DIR", str(fs.state))
    for job_id, state in (jobs or {}).items():
        fs.set(job_id, state)
    return fs
