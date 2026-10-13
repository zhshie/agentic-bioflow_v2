# 007b follow-up 2: progress (executor)

Plan: `followup2-plan.md`. Test cases: `followup2-test-case.md`. Branch `fix/007b-unforward`.

## TC-U2-06 / TC-U2-01 on the unchanged on_site.sh (2026-10-13), after the fake ssh was made to behave like OpenSSH

Fake ssh (`platform/tests/station_harness.py`): `-O forward` records the `-R` spec and the port it gave (spec port 0 -> 41234, 41235..;
else the spec's own port) in `fwd_specs`/`listening`; `-O cancel` succeeds only for a spec equal to a recorded one, otherwise it writes the
two stderr lines and still exits 0. Switches: `cancel_refuse_once`, `cancel_error`, plus `cancel_refuse_text` (TC-U2-17) and
`cancel_warning` (TC-U2-18). `FakeSite.listening()` is the truth for the tests.

`tests/test_station_channel.py -k tc_u2_01` on main's on_site.sh (RED, as required):

    AssertionError: assert (1 == 1 and '-R 127.0.0.1:0:127.0.0.1:8787' in '-O cancel -o ControlPath=.../cm -R 127.0.0.1:41234:127.0.0.1:8787 tester@fake.example')

(the corrected `test_tc038_unforward_cancels_the_forward_and_removes_the_records` fails the same way). Whole file on main's code: 17 failed, 33 passed;
TC-U2-06 (the fake itself) passes.

## Items

- [x] Fake ssh like OpenSSH (`station_harness.py`), tests TC-U2-01..20, 30, 33, 51 in `platform/tests/test_station_channel.py`; `test_tc038_unforward...` corrected (spec `...:0:...`, plus `listening() == []`), nothing else loosened, no test removed.
- [x] `scripts/on_site.sh`: `--forward` also records `cancel_spec=` in `forward_state`; `--unforward` cancels with that spec (old records: port 0 + `local_port`), decides by the master's stderr and exit code (not the exit code alone), no extra sshd connection (only `-O` calls). Refused/erroring cancel: records kept, stderr "... is still open" / "may still be open" with the port, exit 1. Master gone: records removed as before. Master replaced: records removed with a note. Port recorded but no `local_port`/spec: "incomplete", kept, exit 1.
- [x] `platform/abf_station/cli.py` `cmd_unforward`: prints stdout and stderr both; script failure -> return 1 and the copy on the site is not touched.
- [x] `docs/PITFALLS.md` entry 41 (TC-U2-53). `docs/PLATFORM.md` unchanged.
- Manual, not mine: TC-U2-34 (diff review), 40, 41, 54 (maintainer on real NCHC).
