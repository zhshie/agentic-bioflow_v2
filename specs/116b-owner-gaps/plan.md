# Plan 116b: close the owner-binding gaps found in the #123 review

- **Slug**: 116b-owner-gaps. **Branch**: `feat/116b-owner-gaps`. Rebase onto **v3** after #123 merges (no stacked PR).
- **Tier**: A (tightening only).
- **Created**: 2026-10-17 by the developer-agent, from the `/code-review` of #123 and the #116 verifier's needs-human list.

## 給維護者
1. 補 #116 的三個洞：送出參數裡的檔案路徑也只能指自己的資料夾；run 名稱重複時不再洩漏別人的 run；用捷徑（符號連結）繞過資料夾檢查的路全部堵上。
2. 多一個指令，可以把沒有擁有者的舊 run 指定給某人。
3. 只會讓規則變嚴，不放寬任何現有的拒絕。

## Changes (each with a red test first)
1. **Path-valued `params`.**
   - For a caller that is not None, every string value in `params` that looks like a path is checked with the same `caller_area()` real-path rule as the samplesheet cells. "Looks like a path" means it contains `/`, starts with `~`, or names an existing file under the site's read roots.
   - Values that point into `uploads_root` must lie inside the caller's own folder. Values that point elsewhere follow the environment's readRoots rule.
   - The terminal and stdio are unchanged.
   - Pipeline reference files outside `uploads_root` (shared genomes under readRoots) still pass.
2. **The run-name check is owner-aware.**
   - When the existing launch with that name belongs to another user, or to nobody, an HTTP caller gets one generic refusal: "this run name is taken; choose another". It names no Slurm id and no state.
   - The caller's own launch keeps today's detailed words.
   - Names stay globally unique: the run folder is shared on the site.
3. **Links.**
   - (a) `_uploads_problem` / `list_site_files` resolve the requested path with `realpath` before the upload-folder check, and the agent's listing does not follow links out of the requested folder.
   - (b) The bundle records, for every upload-area path (the samplesheet cells and the path-valued params), the real path resolved at request time. The approved hash covers those real paths.
   - (c) The agent, at job time, re-resolves each upload-area path. It refuses the job, with a plain reason, when the resolved real path differs from the recorded one or lies outside the recorded owner's folder. This closes the swap-after-approval gap.
   - The agent check is a refusal only. It never widens what the agent may read.
4. **`abf-platform runs assign RUN_NAME --user USER`** (terminal only).
   - It sets `launches.user_id` on the newest launch row of that run, when the row is NULL.
   - A row that already has an owner needs `--force`, which prints the old and new owner.
   - An unknown user or run is refused.

## Checks
- Each review scenario is a red test: Bob's `params` pointing at Alice's file; Bob reusing Alice's run name; a link in Alice's folder to Bob's folder; a swap between approval and job time.
- No existing refusal is loosened. Rewritten pins go in the ledger with old, new and reason.
- `bash tests/run_all.sh` is green.

## Not in this PR
- Per-user site folders for a remote station (009h).
- Roles and sharing (010).

## Ruling after the #125 code review (2026-10-18, developer-agent). Fix in this PR, each with a red test first
1. `abf_station/handlers.py` `_real_path`:
   - Resolve with NUL-separated output (`realpath -z -m`), or with one call per path.
   - Require exactly the expected number of results.
   - Fail closed: if realpath fails or the count is wrong, the request is refused, never checked the v3 way.
   - Never take an allowed root from realpath output except the roots' own resolution, matched by position.
2. `abf_station/launch.py` `_check_upload_paths`:
   - The same NUL-separated or per-entry resolution.
   - `len(now) == len(entries)` exactly, and the full lists are compared.
   - Fail closed.
3. `abf_launch/build.py` `_param_path`. Replace the "contains `/`" heuristic. A str param is a path when any of these holds:
   - it starts with `/` or `~`;
   - it is `.` or `..`, or has a `.`/`..` path component;
   - it starts with `./` or `../`;
   - it names an existing file or directory under the caller's area or a read root;
   - it contains `/` and is not a scheme URL (`xxx://`) and does not match `^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$` (an `owner/name` identifier such as `nf-core/rnaseq`).

   Path-valued values are confined as before. `owner/name` identifiers and scheme URLs pass. Tests must cover `..`, `.`, a directory name, `nf-core/rnaseq`, `https://x/y`, `s3://b/k` and `data/x.fq`.
