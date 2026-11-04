# cb-D5 ledger

## RED (base 375bfde7)
```
GITHUB_NAME_RE accepts 'nf-core/rnaseq'                    ok
GITHUB_NAME_RE accepts 'a/b.c-d_e'                         ok
GITHUB_NAME_RE rejects 'nf-core/rnaseq\n'                  FAIL
GITHUB_NAME_RE rejects 'a/b\n'                             FAIL
REV_RE accepts '3.14.0'                                    ok
REV_RE accepts 'v1.2.3'                                    ok
REV_RE accepts 'feature/x+y'                               ok
REV_RE accepts 'dev'                                       ok
REV_RE rejects '3.14.0\n'                                  FAIL
REV_RE rejects 'dev\n'                                     FAIL
SHA_RE accepts '0123456789abcdef0123456789abcdef01234567'  ok
SHA_RE accepts '0123456789ABCDEF0123456789ABCDEF01234567'  ok
SHA_RE rejects '0123456789abcdef0123456789abcdef01234567\n' FAIL
SHA_RE rejects '0123456789abcdef0123456789abcdef0123456'   ok
SHA_RE rejects '0123456789abcdef0123456789abcdef012345670' ok
IMMUTABLE_REV_RE accepts '1'                               ok
IMMUTABLE_REV_RE accepts 'v1.2'                            ok
IMMUTABLE_REV_RE accepts 'V3.14.0.1'                       ok
IMMUTABLE_REV_RE rejects '1.2\n'                           FAIL
IMMUTABLE_REV_RE rejects 'v3\n'                            FAIL
IMMUTABLE_REV_RE rejects '1.2.3.4.5'                       ok
TIMESTAMPED accepts 'params_2026-01-01.json'               ok
TIMESTAMPED accepts 'execution_report_x.html'              ok
TIMESTAMPED accepts 'pipeline_dag_a_b.txt'                 ok
TIMESTAMPED rejects 'params_2026-01-01.json\n'             FAIL
TIMESTAMPED rejects 'execution_trace_x.txt\n'              FAIL
TIMESTAMPED rejects 'params_x.csv'                         ok
is_immutable rejects a newline tag                         FAIL
is_immutable accepts a SHA and a tag                       ok
TIMESTAMPED still groups kind and stamp                    ok
methods_text.assets_dir is gone                            FAIL
methods_text.py has no ^...$ literal                       FAIL: ['^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_.-]+$', '^[A-Za-z0-9][A-Za-z0-9._/+-]*$', '^[0-9a-fA-F]{40}$', '^[vV]?[0-9]+(\\.[0-9]+){0,3}$']
collect_provenance.py has no ^...$ literal                 FAIL: ['^(execution_report|execution_trace|execution_timeline|params|pipeline_dag)_(.+?)\\.(html|txt|json)$', '^\\s*(10\\.\\d{4,9}/\\S+?)\\s*(#\\s*(.*))?$']

FAIL
```

## Fix commit
7aba0822 Fix: end methods_text and collect_provenance validators with \Z; drop dead assets_dir

## Targeted tests after fix
methods_text_anchor_test.sh, regex_end_anchor_test.sh, package_gaps_test.sh: all rc=0

## Full suite (HEAD 7aba0822, 136/144 passed, 8 failed - NOT green locally)
Failures are environmental and identical in kind to cloud-burn D1/D3 runs on unrelated code: agent_ctl_connection_id (USER unbound), why_pending, wsl_bridge (rsync/MSYS), platform_clock/platform_test/platform_shard_5-7 (station/cli snapshot/read-only cache tests as root, not touching these files). None touch methods_text, collect_provenance, package_gaps or regex_end_anchor.
```
FAIL       agent          not running - Platform will show no outputs (scripts/on_site.sh --script scripts/agent_ctl.sh start)
FAIL       resources      tar: Child returned status 141
FAIL       compute-env    ce is 'unreachable'>>
missing rsync on MSYS is FAILed by name                    ok
and it says plainly that Git Bash ships none               ok
and gives an install route rather than nothing             ok

-- (i) install_deps.sh: tw on MSYS is named plainly, not folded into 'unknown platform' --
install_deps.sh --cli-only fails cleanly, not silently     ok
it names the gap as unmeasured (R4), a real answer         ok
and gives the Windows asset to fetch by hand               ok
it does not fall back to the generic unknown-platform text ok
shim does not run wsl.exe from the caller's own cwd        ok
and lands in a directory that exists                       ok
only settings.sh decides whether the bridge is in play     ok
and nothing hardcodes the control-path default beside it   ok

3 failed

136/144 passed, 8 failed
```
