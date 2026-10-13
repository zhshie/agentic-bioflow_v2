# 007b follow-up 2: `abf-station unforward` says "cancelled" but the forward stays open (A-tier, no spec change)

Found in the manual acceptance on NCHC, 2026-10-13 21:07 (TC-049). Brings the code back to what `spec.md` and
`docs/` already promise: unforward ends the reverse forward, and a failure is reported, not hidden.

## What happened (real OpenSSH 8.9p1, WSL Ubuntu 22.04, site lgn304)
1. The forward had been opened by `on_site.sh --forward 8787` as `ssh -O forward -R 127.0.0.1:0:127.0.0.1:8787` (port 0 =
   let sshd choose; it chose 41179).
2. `abf-station unforward --deployment ~/abf-station-test` printed "reverse forward cancelled and its records removed",
   exit 0, and removed forward_port/forward_state locally and the copy on the site.
3. `ss -ltn` on lgn304 still showed `127.0.0.1:41179 LISTEN`, held by the master's sshd. The forward was now an orphan
   with no record anywhere.
4. By hand: `ssh -O cancel -R 127.0.0.1:41179:127.0.0.1:8787` → stderr "mux_client_forward: forwarding request failed:
   port not forwarded / muxclient: master cancel forward request failed", **exit code 0**. Then
   `ssh -O cancel -R 127.0.0.1:0:127.0.0.1:8787` → exit 0, and the port was gone from `ss`.

## Three defects
- D1 `scripts/on_site.sh` unforward cancels with the allocated port; OpenSSH matches the spec the forward was opened
  with (port 0).
- D2 `ssh -O cancel` exits 0 even when the master refuses, so the exit code cannot tell success. The script then prints
  "cancelled" whatever happened.
- D3 `abf_station/cli.py cmd_unforward` prints stdout, or stderr only when stdout is empty, so the script's warning is
  never shown; it returns 0.
- Test gap: `tests/test_station_channel.py::test_tc038_unforward...` asserts the wrong spec (`127.0.0.1:41234:...`), and
  the fake ssh accepts any cancel. The fake must behave like real OpenSSH here: a cancel only succeeds when its -R spec
  equals the one given to `-O forward`, and a refused cancel writes the two stderr lines above and exits 0.

## Wanted
- Cancel with the same spec the forward was opened with (record what is needed in forward_state when forwarding).
- Decide success by evidence, not by exit code: the mux stderr saying failed, and/or a check on the site that the port
  no longer listens (`ss -ltn`, read-only). How is the executor's choice; it must not add an sshd session per poll.
- On failure: say plainly that the forward is still open and on which port, keep the records (so `--check-forward`,
  a retry, and the person can still find it), exit non-zero. `abf-station unforward` shows that message and exits non-zero.
- On success: unchanged messages and behaviour.
- Records written by the current code (forward_state without the new field) must still be cancellable: fall back to
  port 0 with the recorded local port.

## Out of scope
Anything in `plugin/`; the relay (`nf_relay.py`) — it already refuses when forward_port is gone (TC-049 run 2 showed 403);
009.

## Constraints for the executor
- Do not touch `~/abf-station-test/`, port 8787, or the NCHC site. Tests use the fake site/fake ssh as today.
- Do not change `.github/`.
