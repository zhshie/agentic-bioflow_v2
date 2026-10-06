# Fix: launch-shapes-unconfirmed

- **Branch**: `fix/gates-audit2-launch` (RED 6037a15, GREEN 500f8d1)
- **Changed**: `hooks/launch_trigger.sh` (`LAUNCH_TRIGGER_RE`, `LAUNCH_VARPROG_RE`, three seqerakit regexes, three HTTP regexes, the per-segment check, both prefilters), `hooks/confirm_launch.sh` and `hooks/confirm_walkthrough.sh` (no-jq text scans), `tests/confirm_launch_test.sh` (32 cases: 19 that must ask, 13 read-only controls; 5 no-jq cases)
- **Approach**:
  - `tw ... actions trigger`, `nextflow ... kuberun`, `nf-core ... launch` (options or `pipelines` between) are verbs of `LAUNCH_TRIGGER_RE`, so they get every existing rule for free (wrappers, nested shells, quotes, the read-only exemption). `nf-core` joins the command words whose quoted program is read with quotes dropped.
  - seqerakit asks when a `.yml`/`.yaml` (or `-`) is among its arguments and neither `--dryrun` nor `-d` is (flags read from seqerakit's `cli.py`: `--dryrun, -d` "Print the commands that would be executed"). `--info`, `--version`, `pip install seqerakit` have no YAML and stay quiet.
  - An HTTP request asks when the quote-free text has a client (curl, wget, http/https/xh, Invoke-WebRequest/Invoke-RestMethod) or a code call (`.post(`, `.request(`, `fetch(`, `urlopen(`, `Request(`), the quote-dropped text a path ending in `/launch`, and a POST (the word in any case - `-X POST`, `--post-data`, `.post(`, `method="POST"`, `-Method Post` - or curl's body flags `-d`, `--data*`, `--json`, `-F`, `--form*`). GET `/workflow/<id>/launch` (describes a launch) stays quiet.
  - Without jq the raw-text scans refuse the same words; an API path ending in `/launch` is refused there whatever the method.
- **Red -> green**: 19 gate cases and 4 no-jq cases failed on 53853d5 (and the same 19 behind a 20 KB here-doc); all 134 `t` cases, 108 identity/egress cases and 44 D3 cases pass now, alone and behind the here-doc. `confirm_walkthrough_test.sh` unchanged and green (its launch backstop G3 now also covers these shapes).
- **Audit probes** (`abf_audit2/probes.txt`, launch lines, WSL): every expected `ask` asks; `make run` still passes, as agreed.
- **Known gap, not changed**: a URL held in a variable set elsewhere (`curl -X POST "$URL"`), and anything hidden in a Makefile or script.
