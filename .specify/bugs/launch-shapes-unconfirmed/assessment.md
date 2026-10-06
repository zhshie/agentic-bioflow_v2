# Bug Assessment: seven ways to start a run pass the launch gate with no confirmation

- **Slug**: launch-shapes-unconfirmed
- **Created**: 2026-10-05
- **Source**: fresh audit against constitution 2.0.0 (`C:\Users\ACER\abf_audit2\probes.txt`, `probe.out`), Safety Net 3
- **Verdict**: valid
- **Severity**: high (each one starts a pipeline run with nothing shown and nobody asked)

## 給維護者

1. 啟動關卡只認得 `tw launch`、`tw runs relaunch`、`sbatch`、`nextflow run`（加上 Seqera MCP 的 launch 工具）。下面這些也會送出一次分析，今天完全不問：
   - 直接打 Platform API：`curl -X POST .../workflow/launch`、`curl -d @launch.json .../workflow/launch`（`-d` 本身就是 POST）、`wget --post-data`、python `requests.post('.../workflow/launch')`；
   - `tw actions trigger`（觸發一個 Platform action，會啟動它綁的 pipeline）；
   - `seqerakit file.yml`（照 YAML 呼叫 `tw`，YAML 裡可以有 launch）；
   - `nf-core launch`、`nf-core pipelines launch`（互動精靈最後會執行 `nextflow run`）；
   - `nextflow kuberun`（在 Kubernetes 上跑）。
2. 只讀的要繼續安靜：`tw runs list`、`curl` GET `/workflow`、`nf-core pipelines list`、`seqerakit --dryrun`/`-d`（seqerakit 原始碼 `cli.py` 的旗標：`--dryrun, -d`「只印出會執行的指令」）。
3. `make run` 不在範圍內：Makefile 裡寫什麼看不到，維持不問。

## Reproduction (WSL, HEAD 490de98, `probe.sh`)

| Command | Today | Should be |
|---|---|---|
| `nextflow kuberun nf-core/rnaseq` | pass | ask |
| `nf-core launch rnaseq` | pass | ask |
| `nf-core pipelines launch rnaseq` | pass | ask |
| `seqerakit launch.yml` | pass | ask |
| `curl -s -X POST -H "Authorization: Bearer $TOWER_ACCESS_TOKEN" "https://api.cloud.seqera.io/workflow/launch?workspaceId=1" -d @launch.json` | pass | ask |
| `python3 -c "import requests; requests.post('https://x/api/workflow/launch')"` | pass | ask |
| `tw actions trigger -n x` | pass | ask |
| `make run` | pass | pass (out of scope) |

## Root Cause (high confidence)

`hooks/launch_trigger.sh` `LAUNCH_TRIGGER_RE` lists only the four verbs; nothing looks at an HTTP request, at seqerakit, at nf-core's launcher, at `kuberun` or at `tw actions trigger`.

## Scope / fix direction

In `is_launch_command`, per segment, on the same two texts the existing checks read (quote-free, and quote-dropped):
- `nextflow ... kuberun`, `tw ... actions trigger`, `nf-core ... launch` (any options or a `pipelines` word between) join `LAUNCH_TRIGGER_RE`.
- `seqerakit` with a `.yml`/`.yaml` (or `-`) argument asks, unless `--dryrun` or `-d` is one of its words.
- An HTTP request asks when the quote-free text has an HTTP client (curl, wget, http/https/xh, Invoke-WebRequest/Invoke-RestMethod) or a code call (`.post(`, `.request(`, `fetch(`, `urlopen(`), the quote-dropped text names a path ending in `/launch` (`/workflow/launch`, `/actions/<id>/launch`), and the request is a POST: the word POST (any case: `-X POST`, `--post-data`, `.post(`, `method="POST"`), or a body flag that makes curl POST (`-d`, `--data*`, `--json`, `-F`, `--form*`). A GET of `/workflow/<id>/launch` (it only describes a launch) stays quiet.
- The no-jq text scan (`looks_launch_shaped`) learns the same words, so it refuses them too rather than letting them through.
- Tests: `tests/confirm_launch_test.sh`, each shape with a read-only control.

## NOT changed

- `make run`, scripts and aliases that hide the verb (cannot be seen from the command line).
- A URL held in a variable (`curl -X POST "$URL"` where `URL` was set elsewhere): the path is not on the line; known gap.
