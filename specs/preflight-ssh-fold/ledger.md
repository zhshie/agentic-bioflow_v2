# preflight-ssh-fold progress ledger

- [x] preflight_site.sh (site-side wrapper, markers `@@preflight-begin/end`, `@@` content lines escaped with one more `@`)
- [x] preflight.sh: ssh branch = one `--script preflight_site.sh`, parsed locally; local branch lines untouched (now an `elif`)
- [x] tests/preflight_ssh_fold_test.sh (TC-001..017, 028, 029)
- [x] docs/PITFALLS.md entry 57
- [ ] TC-024 manual check on a real ssh deployment: not done by the executor (must not reach a site)

## Fake ssh (TC-022)
Chosen: the fake ssh runs the remote command through the local `bash -c` (that command unpacks the tar itself), after logging `$*` to `ssh.calls`. The test copies `scripts/` and `configs/` to a temp tree and puts stubs for the three site scripts there, steered by flag files. `-O check` answers 0 unless `master.down`. Sessions = lines of `ssh.calls` without `-O check`.

## Test at base (RED commit, impl removed): 19 failed / 65 ok
Red: TC-001 (got 4, wanted 2), TC-007 (4), TC-009 (exit 0 / no fixed texts / 4 sessions), TC-029, TC-010 (no preflight_site.sh), TC-011, TC-017 (no bundle), TC-028.
Green at base (guards): TC-002..006, TC-008, TC-012 (the marker-looking text is just egress text at base), TC-013, TC-014, TC-015, TC-016.
TC-013/014/015 compare the new preflight.sh with `git show 223369324548:scripts/preflight.sh` run on the same stubs (stdout+stderr and exit code, 10 situations): identical; diff empty. Skipped with a message when the base commit is not in the checkout.
TC-010 uses the real, unstubbed egress_ctl.sh (status of a relay that is not running): same text both ways.
Note TC-016: in a dry run the contract call prints nothing of its own, so only egress and agent calls are visible there; the test asserts the bundle is absent and the OK resources line present.

## After
Focused: preflight_ssh_fold, preflight_reach, on_site, site_report, credentials_stay_in_settings, no_second_run_state, no_hardcoded_paths, command_layer_is_site_neutral, launch_recheck, bash32_arrays: all pass in WSL.
Decision of note: when any of the three sections is missing its end marker, all three are reported FAIL (plan step 3, TC-029), even if one arrived whole.
