# cb-D3 ledger

## RED (base 62c91293, tests only)
```
test_regex_anchor_fixes.py::test_plain_rejects_trailing_newline[txt\n]
test_regex_anchor_fixes.py::test_plain_rejects_trailing_newline[a.b\n]
test_regex_anchor_fixes.py::test_plain_rejects_trailing_newline[A_b-c\n]
test_regex_anchor_fixes.py::test_extensions_reject_trailing_newline[*.txt\n]
test_regex_anchor_fixes.py::test_extensions_reject_trailing_newline[*.{gz,txt\n}]
test_regex_anchor_fixes.py::test_extensions_reject_trailing_newline[*.fa\n]
test_regex_anchor_fixes.py::test_bucket_rejects_trailing_newline[abc\n]
test_regex_anchor_fixes.py::test_bucket_rejects_trailing_newline[a-b\n]
test_regex_anchor_fixes.py::test_bucket_rejects_trailing_newline[my-bucket\n]
test_regex_anchor_fixes.py::test_bucket_rejects_trailing_newline[aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n]
test_regex_anchor_fixes.py::test_bucket_rejects_trailing_newline[aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n]
test_regex_anchor_fixes.py::test_source_literal_ends_with_end_of_string_anchor[validate.py-_PLAIN]
test_regex_anchor_fixes.py::test_source_literal_ends_with_end_of_string_anchor[cloud_store.py-_BUCKET]
13 failed, 20 passed in 0.14s
```

13 new tests fail on unchanged code (trailing-newline acceptance + source literal); the 20 regression-shape tests pass on base, as intended.

## Calibration: old shapes against base and branch (/tmp/cb/D3_cal/shapes.py, 47 shapes: _PLAIN, _BUCKET, _container_ok, _extensions, parse_gs)
Diff base -> branch changes only these shapes, all of them "valid name + exactly one trailing newline", all now rejected:
`_PLAIN "txt\n"`; `_BUCKET`/`_container_ok` "abc\n", "a-b\n", 62-a+"\n", 63-a+"\n"; `_extensions("*.txt\n")`, `_extensions("*.{gz,txt\n}")` (True/set -> False/None).
Everything else is identical: all non-newline accepts (txt, a.b, A_b-c, 63-char bucket, ...) and rejects (empty, space, slash, non-ASCII, 64-char bucket, uppercase, "\n\n", "\r", leading/embedded newline) and parse_gs results (it already rejected newlines through its control-character check).

## GREEN
pytest test_regex_anchor_fixes + test_validate + test_cloud_upload: 154 passed. tests/regex_end_anchor_test.sh: ok x3 (no stale baseline lines, no new hits).

## Full suite (tests/run_all.sh at the fix commit's tree, HEAD before commit d2553bc9 + fix)
NOT GREEN LOCALLY: 132/141 passed, 9 failed. Last 20 lines of /tmp/cb/D3_runall.txt:
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

132/141 passed, 9 failed
```
Failing entries: agent_ctl_connection_id_test, why_pending_test, wsl_bridge_test, platform_clock_test, platform_shard_4/5/6/7,
platform_upgrade_test.
- Re-run on a clean origin/v3 checkout (same VM): agent_ctl_connection_id_test, why_pending_test, wsl_bridge_test fail (USER unbound,
  no rsync, ...); pytest test_cli_snapshots[cli_help_top], test_station_launch tc022, test_station_resume tc026,
  test_pipeline_launch_station tc124 and test_station_e2e tc056/tc082 fail too (running as root, read-only-cache tests cannot work;
  help snapshot). So the platform_clock/shard_4-7 failures are the VM, not this change.
- platform_upgrade_test TC-U28 ("platform/, backup.sh and deploy/systemd untouched") fails because it diffs the merge base against
  the work tree and any edit under platform/ trips it: platform/abf_platform/validate.py, cloud_store.py and the new
  platform/tests/test_regex_anchor_fixes.py. It cannot pass for any task that changes platform/; not weakened, not edited
  (tests/ is outside this task's files). See FINDING.
- Everything that touches this change is green: regex_end_anchor_test.sh ok x3, test_regex_anchor_fixes.py, test_validate.py,
  test_cloud_upload.py (154 passed), and the platform shards that contain them.
