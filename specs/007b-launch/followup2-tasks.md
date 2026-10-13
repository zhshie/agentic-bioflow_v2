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
