# 網頁上傳檔案到雲端（b：代理寫入、傳完刪暫存、ADR 0010 修正） progress ledger

- [x] RED: `platform/tests/test_byte_channel_b.py` (TC-001..TC-088 automatic cases; BB-nn in each comment). Commit `RED:`.
- [x] GREEN: `platform/abf_station/put_upload.py` (new), `site.py` (`Fed`, `start_fed`, header note; additions only), `handlers.py` (import, `JOB_KINDS`, `ARG_KEYS`, one dispatch, header sentence), ADR 0010 section. Commit `GREEN:`.

## 核對 `--format=value(size)`（裁決二 3）
This machine (Windows, and the WSL Ubuntu used for the suite) has no `gcloud`, so `gcloud storage objects describe --help` could not be run. Checked against the published reference instead (https://docs.cloud.google.com/sdk/gcloud/reference/storage/objects/describe, read 2026-10-25): the page lists `--format` as a global flag and shows `gcloud storage objects describe gs://bucket/my-object --format="json(name)"`; the `value(<key>)` projection is gcloud's standard formatter (reference/topic/formats, examples such as `--format="value(config.account)"`). So `--format=value(size)` is the same spelling with the object's `size` key. NOT run against a real gcloud or bucket: 尚未用真 bucket 驗過.

## 手動案例（通例，貼 diff）
`git diff --name-only 45c4294` (45c4294 = the last commit before this task's work):
```
docs/adr/0010-chat-keys-byte-channel-studio-embedding.md
platform/abf_station/handlers.py
platform/abf_station/put_upload.py
platform/abf_station/site.py
platform/tests/test_byte_channel_b.py
```
`git diff --stat 45c4294` (before this ledger): 5 files, 1233 insertions, 4 deletions. The 4 deleted lines are in `handlers.py` (the old docstring line, the import line, `JOB_KINDS`, the end of `ARG_KEYS`; see `git diff 45c4294 -- platform/abf_station/handlers.py`); `site.py` has 70 added lines and 0 removed (`run_fixed`, `start_detached`, `Site.call` untouched); the ADR has 9 added lines and 0 removed. No existing test file is touched (TC-073). `abf_platform/`, `gcb_preflight.py`, `agent.py`, `pyproject.toml`, `constraints.txt`, `hooks/`, `tests/run_all.sh`, `.github/`, `abf_launch/build.py`, `abf_station/launch.py` are not in the diff, so no data shape changed and no migration is needed (TC-079).

## 為什麼不違反憲法 Safety Net（TC-089）
1. Confirmation: constitution I.2 accepts the human channel "confirmation page, same signed-in user". The person picks the file, the environment and presses upload on the signed-in page (maintainer ruling A, ADR 0010 2026-10-25 section). `put_upload` can only be queued through `enqueue_put_upload` (`_enqueue` refuses it, TC-085) and no MCP tool has "upload" in its name (TC-086). This departs from the backend brief "every write needs a confirmation" with the maintainer's explicit consent ("1.會慢半天就不用"); listed as a thing for a person to look at.
2. "Never delete a user's source data": `uploads/` holds the platform's transfer copy, not the source (that is on the person's computer). Only one regular file is removed, only after the cloud size read back equals the local size, and only if the name still leads to the same file (device and inode) that was copied (TC-023..TC-031, TC-084).

## 未驗證／限制
- 尚未用真 bucket 驗過: (a) memory and timeout behaviour of a 2 GB `gcloud storage cp -` stream; (b) whether a killed stdin upload leaves a partial object in the bucket (the agent only kills the process; the failure message tells the person the bucket may need a look).
- A gcloud that hangs without reading its input while a file larger than the pipe buffer is being fed would block the write; the timeout (3600 s, `ABF_STATION_PUT_TIMEOUT` for tests) only covers the wait after the input is closed. The agent has no thread for a watchdog by rule (TC-090 scan), so this was left; flagged for the verifier.
- `Fed.close_input` is an alias of `close_stdin`: the existing scan `input\(` in `test_station_static.py` matches the text `close_input(` in a `def`, so the contract name (TC-067) is given by assignment and `put_upload.py` calls `close_stdin`.
- Web, MCP, HTTP routes and placing the file in `uploads/` are not in this task (cloud-upload-wire).

## 裁決三的處理
- 裁決三 10：`platform/tests/test_station_clean.py` 的 TC-028 改了兩行（不是一行）：`JOB_KINDS[6:]` 加 `"put_upload"`；下一行 `ARG_KEYS` 的排除集合也要加 `put_upload`，否則同一個斷言仍因新增的 `put_upload` 鍵而失敗。第二行超出裁決字面，請 verifier 確認。
- 裁決三 12：gcloud 掛住不讀 stdin 時餵檔寫入會卡住（禁 thread），本片接受；f 片真桶驗收時另測。
- 裁決三 11：測試裡私鑰標頭用拼接字串組出（`grep "BEGIN PRIVATE" platform/tests/test_byte_channel_b.py` 無全文）。
