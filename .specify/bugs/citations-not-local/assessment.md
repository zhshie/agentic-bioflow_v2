# Bug Assessment: finish cites nothing because the pipeline was never pulled on this machine

- **Slug**: citations-not-local
- **Created**: 2026-10-05
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/4
- **Verdict**: valid
- **Status**: fixed; reopened once after independent acceptance (see fix.md, round 2)
- **Severity**: high for the default deployment (every first `finish` of every user lands in it); no data is wrong, but the package says "[CITATION NEEDED]" for tools that are well documented upstream and blames nothing true

## 給維護者

1. 本外掛的設計是管線一律經 Seqera Platform 在遠端跑，本機從不執行 `nextflow pull`；但 `finish` 要的 `CITATIONS.md` 與方法段範本只有本機 `nextflow pull` 才會放進 `~/.nextflow/assets`。所以每個照設計使用的人，第一次 `finish` 都是「每個工具都 [CITATION NEEDED]」。
2. **牽涉的憲章條文：第 7 條（Principle III，「Nobody should need the maintainer」，A Person Can Finish）。** 使用者目前得先自己想通原因、手動 curl 兩個檔案才能完成；這正是第 7 條禁止的。同時涉及第 11 條所在的 Principle V（只寫部署自己擁有的地方，不寫進 `~/.nextflow`）與第 1 條（`launch` 已有「從管線自己的 repo 讀檔」這招，不另造一套）。
3. 修法：缺檔時，用執行紀錄自己記錄的管線與版本，從管線的 GitHub repo 取回這兩個檔，存進部署自己的快取 `<root>/cache/pipeline_files/`；仍先讀 `~/.nextflow/assets`（只讀、不寫）。任何失敗（沒有版本、不是 owner/repo、404、離線）都不中斷打包，並在 Notes 寫出真正原因。
4. 需要你決定的一點：快取放在 root 底下的 `cache/`（新目錄）。它是可丟棄的，但 root 通常在雲端同步資料夾裡，所以快取檔會被同步。若不想，可改放機器本地目錄；我選 root 是因為它是設定檔裡「部署擁有」的唯一位置。

## Findings

`scripts/methods_text.py` defaulted `--assets` to `~/.nextflow/assets` and looked for `<pipeline>/CITATIONS.md` and `<pipeline>/assets/methods_description_template.yml` only there. Nothing in `setup` or `launch` puts them there (the pipeline runs on the cluster through Platform). The note it wrote ("no CITATIONS.md for X under ~/.nextflow/assets - every tool below is unmatched for that reason alone") was honest about the cause but the cause is the default state, not an edge case.

`commands/launch.md` already solves the same problem for `nextflow_schema.json` and `assets/schema_input.json`: `scripts/prepare_launch.sh` reads them from `raw.githubusercontent.com/<repo>/<revision>/...` with curl. `finish` never got the same step.

## Reproduction (WSL)

1. A run whose `software_versions.yml` has `Workflow: nf-core/demo: v1.2.3`, with `--assets` pointing at an empty directory.
2. `scripts/methods_text.py --assets <empty> <run>/results`: every tool is `[CITATION NEEDED: ...]`, note says "no CITATIONS.md for nf-core/demo under <empty>".
3. Expected: the files are fetched at `v1.2.3`, the slot is filled, and the Software section names where the citations came from.

## Scope

In: `scripts/methods_text.py` (resolve, fetch, cache), `scripts/build_package.sh` (passes the cache location), `commands/finish.md`, `docs/FINISH.md`, `docs/SETTINGS.md` (the cache directory), the "Nothing existing" header on `methods_text.py` and `detect_conditions.sh`.

Out: `~/.nextflow/assets` stays read-only. No change to citation matching. `launch`'s own fetch (which deliberately caches nothing, constitution 6) is not touched.

## Failure cases that must stay visible and never stop the build

| Case | Reason written into the Notes |
|---|---|
| versions file records no revision for the pipeline | no revision, nothing to fetch |
| pipeline name is not `owner/repo` (or contains `..`) | not a GitHub owner/repo |
| 404 at the revision | file not found at that revision |
| no network / proxy refusing | network unreachable, with curl's own message |

## Proposed Remediation

Red first: `tests/methods_text_fetch_test.sh` with a fake fetcher (no network): success, 404, offline, second run served from cache, tag vs commit SHA, a name that is not owner/repo, no revision, local copy first, template fetched only when the report did not already render it, cache location under the root. Then the fix.
