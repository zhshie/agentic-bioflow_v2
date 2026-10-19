# 012c-uploads-backend: pair FASTQ, register a Dataset, refuse web uploads over 2 GB

(The maintainer's later chat question about dev.cmd was already answered by the developer-agent; it is not an instruction for this task. Proceed with the task.)

Backend only, tier A (no MCP tool, no web route, nothing a user sees yet). Files: NEW `platform/abf_platform/actions/datasets.py`, NEW `platform/tests/test_datasets.py`, `specs/012c-uploads-backend/`. Do NOT edit actions/__init__.py, mcp_server.py, web.py, web_board.py, store.py (other sessions own them).

## Maintainer quote (approved 2026-10-18, verbatim)
「專案按「上傳資料」→ 拖進 4 個 FASTQ（各約 500 MB）→ 顯示進度、完成後列出 4 檔 → 按「建立樣本表」，平台自動把 R1/R2 配對 → 他檢查後存成一份資料集（Dataset）。超過 2 GB：網頁不收，改給一行指令讓他在國網或自己電腦上傳。檔案直接存到國網他自己的資料夾；平台只記檔名與位置，不另存一份。」

## Facts (checked on origin/v3)
- Byte transfer through the station agent does not exist (ADR 0010; upload job kind is later work). This slice never reads or writes file content and never calls open()/os.stat on uploads.
- Reuse `caller_area(platform_path, caller)` and `confined_samplesheet(platform_path, caller, path)` from `abf_platform.actions` (import them lazily inside functions to avoid a cycle). `store.connect_state`, `store.uploads_root`. Caller: `caller.user_id`/`caller.name`; None = terminal/stdio, sees everything. A missing item and somebody else's item get identical words. Tests reuse `Duo` from platform/tests/owner_harness.py and sql_rows/sql_exec helpers.
- ADR 0009 pt 5: datasets record paths (and checksums when available) only; a samplesheet is stored whole per version.
- Large-file path: `scripts/push.sh [--dry-run] <local-path> <site-path>`.

## Design: actions/datasets.py (bilingual 中文+English messages in the existing style; caller=None and clock=time.time params)
1. `pair_fastq(files) -> {pairs:[{sample,fastq_1,fastq_2}], unpaired:[{file,reason}], csv}` pure. Tags `_R1_001/_R2_001`, `_R1/_R2`, `_1/_2`; ext .fastq(.gz)/.fq(.gz). Sample = stem minus tag minus trailing `_S\d+(_L\d{3})?`. Pair only same folder + same stem. Never guess: report no tag, I1/I2/R3, missing mate, two candidates for one mate, mixed tag styles. Lane files of one sample (_L001/_L002) become repeated rows with the same sample name. CSV columns only sample,fastq_1,fastq_2.
2. `draft_samplesheet(platform_path, files, *, caller=None)` confines each name (relative = caller's folder), pairs, returns {ok,csv,pairs,unpaired}; outside the area -> {ok:False,message} naming only the caller's own folder. Writes nothing.
3. `check_web_upload(platform_path, sizes, *, caller=None)`; sizes = browser-reported {name: bytes}. WEB_UPLOAD_LIMIT = 2_000_000_000 PER FILE (decimal). Any file over -> {ok:False, over:[...], command}, command = `bash scripts/push.sh <你電腦上的資料夾> <caller_area>/rawdata` built from caller_area (no literal path), plus a second sentence: already on the cluster -> copy the files into that same folder. Exactly 2_000_000_000 is accepted.
4. `register_dataset(platform_path, *, name, version, samplesheet, files, caller=None, clock=time.time)`; files=[{path, size_bytes?}]. Validate name/version `^[A-Za-z0-9._-]{1,64}$`; samplesheet CSV with sample and fastq_1 columns, <=1 MiB; every file confined; every path cell in the samplesheet is among the registered files; no URL cell; no credential-shaped value (use compute_envs.looks_like_credential). Duplicate (owner,name,version) refused (handle NULL owner in the same transaction); versions immutable. Returns {ok, dataset:{name,version,n_files,created_at}}. No human-channel gate: it saves metadata and submits nothing.
5. `list_datasets(platform_path, *, caller=None)`, `get_dataset(platform_path, name, version=None, *, caller=None)`: HTTP caller sees only own owner_user_id; None sees all; owner-NULL rows hidden from HTTP callers; no version = newest.

## Storage
New table `datasets` in platform.db created by the module with CREATE TABLE IF NOT EXISTS on the connection from store.connect_state (store.py not edited): id, owner_user_id, name, version, samplesheet_csv, files_json, created_at, UNIQUE(owner_user_id,name,version). A dataset is an input description, not run state: no status, no run id. tests/no_second_run_state_test.sh must stay green.

## Tests first (platform/tests/test_datasets.py)
TC-001 4 files a_R1_001/a_R2_001/b_R1_001/b_R2_001.fastq.gz -> 2 pairs a,b, header sample,fastq_1,fastq_2. TC-002 same for _R1/_R2, _1/_2, .fq.gz. TC-003 lone x_R1.fq.gz -> unpaired with reason, not in CSV. TC-004 two R1 candidates of one stem both reported, none paired; mixed styles not guessed. TC-005 I1/I2 and untagged -> unpaired. TC-006 _S1_L001 stripped; two lanes -> two rows same sample. TC-007 path outside caller area refused by draft and register (../, absolute into bob's folder, symlink in alice's folder to bob's), no row written, message names only caller's folder. TC-008 2_000_000_001 bytes refused with scripts/push.sh and caller's own area path; 2_000_000_000 accepted. TC-009 register -> one row right owner; list shows; get returns samplesheet+locations. TC-010 bob sees nothing of alice's; his get = same words as missing. TC-011 duplicate name+version refused; new version accepted; get without version = newest. TC-012 a real FASTQ with a marker string registered: DB bytes contain neither marker nor abf_pat_; URL or token-like value in a cell or name refused; file bytes/mtime unchanged. TC-013 samplesheet cell naming an unregistered file refused; bad name/version; samplesheet without fastq_1 refused. TC-014 `from abf_platform.actions import datasets` works with actions/__init__.py byte-identical to origin/v3; module has no submit/queue/job code and no literal /home path. TC-015 caller=None registers (owner NULL) and sees all; HTTP caller does not see that row. TC-016 source scan: no open( or os.stat in the module; an unreadable path still registers.

## Out of scope
Byte transfer, relay, checksums, existence check of remote files, linking runs to dataset versions, delete/share/edit, MCP tools, web routes, docs/PLATFORM.md, CHANGELOG.md.

## Revision 2026-10-19: make TC-064 / TC-066 CI-safe (re-land of PR #143)
PR #143 was merged with red CI and reverted (#147). This branch re-applies it (commit "Revert \"Merge pull request #147\"") and fixes the only failure: `test_tc064_other_sessions_files_are_untouched` and `test_tc066_docs_and_changelog_are_untouched` run `git diff origin/v3`, but the CI checkout has no `origin/v3`, so both fail in CI, and after merge a diff against v3 is meaningless anyway.
Do:
1. TC-064: keep the part that checks a lasting property — the five named files (actions/__init__.py, mcp_server.py, web.py, web_board.py, store.py) do not contain any of the datasets function names / `actions.datasets`. Remove the `rev-parse origin/v3` assertion and the `git diff --stat origin/v3` assertion. Comment: "branch-scope diff is the verifier's job (git diff at review), not a lasting property".
2. TC-066: remove the test (it only checks that this branch did not edit docs/PLATFORM.md and CHANGELOG.md, a review-time scope check with no lasting meaning). Record in test-case.md that TC-066 moved to the verifier's review checklist, and why.
3. Remove the now-unused `git()` helper only if nothing else uses it.
4. No product code changes. Full `bash tests/run_all.sh` green. Then also prove CI-likeness: run `platform` pytest for test_datasets.py inside a fresh `git clone --depth 1 --branch feat/012c-datasets-redo` of the local worktree path (a checkout with no origin/v3) and show it passes.
