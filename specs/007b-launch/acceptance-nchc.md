# 007b manual acceptance on NCHC (2026-10-13)

Site: Taiwania 3, login node lgn304, account u9613010, project MST109178. Platform and agent in WSL Ubuntu 22.04
(OpenSSH 8.9p1), main e856608 unless noted. Procedures: `docs/TESTING.md` half 2, steps 1-3.

## TC-047 ampliseq runs to the end — PASS
- Run `ampliseq-mt-0920-r2` (nf-core/ampliseq 2.18.0, the 2026-09-20 settings). The first try was refused by the
  agent's preflight because the shared SSH connection had expired; that refusal was shown as "result unknown" and
  led to follow-up 1 (#86).
- Succeeded; 71 tasks in `get_run` = 71 rows of `trace.txt`, all COMPLETED; `results/` has 12 folders; run folder
  mode 700; the run token found only in `tower.token`.
- Note: `slurm-*.out` is 644 and `head.sh` 711 inside the 700 folder (nothing readable from outside); may be tightened.

## TC-048 cancel a small run — PASS with notes
- Run `tc048-cancel-2`; cancelled at 16:03:51 while DADA2_MERGE had just been submitted. Head job 2233365 left the
  queue about 2 s after the request; all of the run's jobs left; other users' jobs stayed.
- `get_run`: failed, 49/50 tasks, 1 pending. `launches` shows the cancel time; run folder kept; token revoked.
- Notes for follow-ups: `get_run` does not show the failure reason; one 401 warning after `complete` (token revoked
  while Nextflow sends one more message); "Report/Timeline file already exists" warnings.
- A first try (`tc048-cancel-test`, job 2233216) was cancelled 14 s after submit while still pending; not counted.

## TC-049 the way back on the real site — FAIL, fixed by follow-up 2, then PASS
- Forward bound to `127.0.0.1:41179` only (`ss -ltn`). PASS.
- Probe job 2234466 on cpn3870 (ngs7G, 1 CPU, 7G), forward open: via relay to the forward `/user-info` → 401 with
  `x-abf-platform`; another port → 403; `/agent/poll` → 403 (relay log `DENY-LOOPBACK` for both); `lgn304:41179`
  directly → connection refused. PASS.
- `abf-station unforward` → printed "reverse forward cancelled", exit 0, but `127.0.0.1:41179` still LISTEN on lgn304,
  records gone. **FAIL** (cause and fix: `followup2-plan.md`, PITFALLS 41). The orphan was cancelled by hand with
  `ssh -O cancel -R 127.0.0.1:0:127.0.0.1:8787`.
- Probe job 2234471, forward gone: all four probes refused (403/403/403/refused). PASS.
- Old relay process case: not reproducible (the relay on the site is already the new one).
- An earlier probe job (2233634) asked for 1G on ngs7G and stayed pending (QOSMinMemory); cancelled by the maintainer.

## TC-U2-54 recheck of follow-up 2 (branch fix/007b-unforward, 21:4x)
- `on_site.sh --forward 8787` → port 45399 LISTEN; `abf-station unforward` → success message, exit 0; port gone from
  lgn304. A second unforward with nothing recorded → exit 0. PASS.
- Refusal on real OpenSSH: forward on 48363, `forward_state` edited to a wrong spec → "the reverse forward on port
  48363 is still open…", exit 1, port still LISTEN, records kept; restored the record → success, exit 0, port gone. PASS.
- Not done on the real site: "connection replaced, then unforward" (needs a new OTP login); covered by TC-U2-15.

## Not done
- TC-050 Seqera comparison.
