---
id: cloud-upload-docs
title: 雲端上傳文件跟上現況：OPERATIONS 的過期句、「資料集放在 bucket」一節、PLATFORM 的 C-6 舊說法、TESTING 的手動步驟改成真指令
tier: A
kinds: docs
lane: L-docs-cloud
base: v3（`origin/v3` @ 2385f97；所有行號都是該版本）。要等 `dataset-cli-launch` 與 `resume-edit-params-d` 都合併後才能開（前者提供文件要寫的指令，後者同改 `docs/PLATFORM.md`、`docs/TESTING.md`）。
source: developer-agent 讀碼查證（2026-10-24）。cloud-upload.md「待 developer-agent 裁決」第 4 項（使用者電腦上 gcloud 帳號從哪來，建議由 docs 任務補）；#188／#199 合併後 OPERATIONS 仍寫「沒有費用估算與上限」
---

# cloud-upload-docs

> A 級（純文件＋一支檢查文件的測試）：CI 綠就由 developer-agent 自合。**文件只寫今天程式做得到的事**；做不到的明寫「還沒做」，不寫願景。

## 目標
讓管理者與使用者讀文件就知道：雲端（Google Batch）的輸入檔怎麼放、放哪、怎麼登記成資料集、上限多大、平台管不管權限；並移除三處已經過期的句子。對使用者的意義：不必問人就知道「檔案放哪個前綴、用哪行指令、哪些事要找 Google Cloud 管理者」。

### 查證結果（皆 `origin/v3`）
過期的句子：
- `docs/OPERATIONS.md:217`（Google Batch 小節最後一句）："the platform has no cost estimate or cap yet."——費用估算與每人每月上限已合併：`platform/abf_platform/actions/__init__.py:598-607`（`_cloud_check` 在確認前查上限並給預估）、`platform/abf_platform/cli.py:131`（`cmd_user_cloud_cap`）、說明在 `docs/CLOUD.md`。`git grep "no cost estimate" origin/v3` 只命中這一句，沒有測試釘著。
- `docs/PLATFORM.md:294`（"Input data" 段）："Copying files into the bucket is a later feature (C-6); for now put them there yourself with `gcloud storage cp`."——C-6 的平台半邊（登記、前綴規則、>2 GB 指令）已合併（#192）；位元組怎麼進 bucket（byte-channel）仍沒做，所以「自己用 `gcloud storage cp` 放」仍是對的，但「是之後的功能」要改成準確的現況。
- `docs/TESTING.md:604-612`（"Datasets in a cloud bucket (cloud-upload)"）：五個手動步驟要使用者進 Python 殼呼叫 `register_dataset(…)`；`dataset-cli-launch` 合併後有真的終端機指令，步驟該改用它。
文件要依據的事實：
- 前綴規則：`platform/abf_platform/cloud_store.py:67-72`（`gs://<bucket>/uploads/<使用者名>/`，終端機無擁有者時 `gs://<bucket>/uploads/`）；bucket 必須是該環境 `workDir` 的 bucket（`cloud_store.py:47` `workdir_bucket`；`actions/datasets.py:130-145` `_cloud_place` 的訊息）。
- 大檔：單檔上限 `WEB_UPLOAD_LIMIT = 2_000_000_000` 位元組（`datasets.py:22`，十進位）；超過回一行 `gcloud storage cp <你電腦上的資料夾>/* <前綴>rawdata/`（`cloud_store.py:92-95`）。
- 平台不碰憑證：`cloud_store.py` 與 `datasets.py` 沒有任何憑證路徑參數（cloud-upload.md 作法 A.8）；平台也沒有任何呼叫 Google IAM 的碼——**平台不授予、不檢查誰能寫 bucket**，那是 Google Cloud 專案擁有者的事。
- 送出時 Google Batch 還會再驗每個路徑儲存格：`abf_station/launch.py:669-693`（必須是 `gs://<workDir 的 bucket>/…`）。
- `dataset-cli-launch` 合併後的指令：`abf-platform dataset register|list|show`，選項 `--name --version --samplesheet --file --user --destination`（見該計畫「作法」3）。**開工第一步**：`abf-platform dataset register --help` 核對上述名字；對不上就 BLOCKED。

## 維護者原話（verifier 出題用）
- 「**雲端上傳＝平台代傳到使用者自己的 bucket、不落地（ADR 0010 規則），大檔給 `gsutil` 指令**」（`PLAN-abf-v3-replan-2026-10.md` 第 58 行，裁示 16）→ T2、T3：文件講「自己的前綴」「大檔指令」；指令用 `gcloud storage cp`（cloud-upload 裁決 3 已定，原話寫 `gsutil`；PR 說明提一句）。
- 「使用者用自己的 AI 走 MCP，不用 AI 的人走網頁」（第 37 行）→ T4：文件說 AI 用 `launch` 的 `dataset` 參數，不寫不存在的工具。
- 本任務沒有針對措辭的逐字裁示；文件的白話程度依 `CLAUDE.md` 回答契約（短、先給結論、行話一句白話）。

## 範圍：檔案
- `docs/OPERATIONS.md`（只改 `### Google Batch on the platform host`〔:215〕這一節，並在它後面加一個 `###` 小節「Datasets in the lab's bucket」；**`##` 標題數維持 6**，`tests/operations_doc_test.sh:20-27` 查）
- `docs/PLATFORM.md`（只改 :294 那一句，以及其附近必要的一句指向 OPERATIONS）
- `docs/TESTING.md`（只改 `## Datasets in a cloud bucket (cloud-upload)` 一節的步驟，:604-612）
- `platform/tests/test_cloud_upload_docs.py`（新；檔首 `# Nothing existing: …` ≥15 字）
- `specs/cloud-upload-docs/ledger.md`
- **不准動**：`docs/INSTALL.md`（`tests/install_doc_test.sh:55` 要求其中每個反引號詞都是 MCP 工具名）、`docs/CLOUD.md`（`test_cloud_cost.py:772-790` 逐字釘著，且不含 "NT$"、"台幣" 數字、"匯率"）、`platform/abf_station/launch.py` 的 `NO_BUCKET_PATH`（:531-532；`test_gcb_launch.py:690` 釘著 "C-6"）、一切程式碼。

## 作法（內容決定）
1. **OPERATIONS.md :217**：刪掉 "the platform has no cost estimate or cap yet."，改成「Before a launch the platform checks each person's monthly cloud cap and shows an estimate (`docs/CLOUD.md`); it does not stop a run that is already going.」。保留 "Java 17"、"Nextflow"、"gcloud"、"storage_root"（`test_gcb_launch.py:1166-1170` 要求 OPERATIONS+INSTALL 含前三者）。
2. **OPERATIONS.md 新小節 "Datasets in the lab's bucket"**（英文，短；每點一句）：①檔案放 `gs://<bucket>/uploads/<user>/`，bucket 就是環境 `workDir` 的 bucket；②每人用自己電腦的 `gcloud storage cp <folder>/* gs://<bucket>/uploads/<user>/rawdata/` 放入（單檔超過 2 GB 平台也只給這行指令）；③登記：`abf-platform dataset register --name … --version … --samplesheet … --file gs://… --user <name> --destination <env>`；④AI 用 `launch` 的 `dataset` 參數；⑤**平台不授予也不檢查寫入 bucket 的權限**，要由 Google Cloud 專案擁有者在 Google 那邊給（文件不寫細節、不寫任何金鑰檔位置之外的憑證內容）；⑥**還沒做**：從瀏覽器直接把檔案送進 bucket（byte-channel，尚未合併）。
3. **PLATFORM.md :294**：「Copying files into the bucket is a later feature (C-6); for now…」改成「The platform does not copy files into the bucket (sending a file from the browser into it is not built yet); put them there with `gcloud storage cp`, then you may keep them as a Dataset (`docs/OPERATIONS.md`, "Datasets in the lab's bucket").」不動該節其餘字（`test_gcb_launch.py:1146-1166`、`test_gcb_ce.py:854-880` 釘著關鍵字）。
4. **TESTING.md 手動步驟**：步驟 1–4 的「call `register_dataset(…)`／`check_web_upload(…)`」改成 `abf-platform dataset register …`（步驟 4 的「超過 2 GB」目前沒有指令入口，保留為「讀 `docs/OPERATIONS.md` 的指令是否與 `cloud_store.big_file_command` 一致」並註明無入口）；每步仍寫「Check: …」；刪掉「in a Python shell」。結尾「The reviewer」那段不改。
5. **英文＋白話**：這三份是英文；不用未解釋的縮寫（第一次出現 "prefix" 就寫成「the folder-like part of the bucket address after `gs://<bucket>/`」）。

## 失敗先行測試（`platform/tests/test_cloud_upload_docs.py`；讀 `REPO_ROOT / "docs" / …`，樣板 `test_cloud_cost.py:769-790`）
| # | 斷言 | 現在 |
|---|---|---|
| T1 | OPERATIONS 不含 "no cost estimate or cap yet"，且含 `docs/CLOUD.md` | 紅 |
| T2 | OPERATIONS 有 `### Datasets in the lab's bucket`；小節含 `gs://<bucket>/uploads/<user>/`、`gcloud storage cp`、`rawdata/`、`2 GB`、`abf-platform dataset register`、`--destination` | 紅 |
| T3 | 該小節含 "does not grant" 與 "not built yet"（權限與瀏覽器上傳兩句） | 紅 |
| T4 | 該小節含 `dataset`（launch 參數）而不含任何不存在的 MCP 工具名（反引號詞 ∩ `mcp_server.py` 的工具名之外，不得有 `register_dataset` 當工具） | 紅 |
| T5 | OPERATIONS 的 `## ` 標題恰 6 個，且仍含 "Java 17"、"Nextflow"、"gcloud" | 綠（鎖住） |
| T6 | PLATFORM 不含 "Copying files into the bucket is a later feature"，且該段含 `gcloud storage cp` 與 "Datasets in the lab's bucket" | 紅 |
| T7 | TESTING 的 cloud-upload 小節不含 "Python shell"，且含 `abf-platform dataset register` | 紅 |
| T8 | 三份文件裡每個 `abf-platform dataset <word>` 的 `<word>` ∈ {register, list, show}，`--destination`、`--user` 在 `cli.py` 的 `dataset` 群真的存在（讀 `cli.py` 文字） | 紅 |
| T9 | 三份文件不含 `@…iam.gserviceaccount.com`（`lab-project-1` 例外，沿用 `test_gcb_launch.py:1166-1170` 的規則）、`abf_pat_[A-Za-z0-9]{8,}` 形狀的字串（沿用 `tests/install_doc_test.sh:72`；文件裡的 `abf_pat_...` 說明字樣不算）、`BEGIN PRIVATE KEY`（TESTING.md 現有的 "private_key" 搜尋提示是「叫人去搜」，不是金鑰內容，保留） | 綠（鎖住） |
| T10 | `NO_BUCKET_PATH` 與 CLOUD.md 的檔案 diff 為空（`git diff --stat` 證據貼 ledger，閱卷者核對） | 綠（鎖住） |

**會改斷言的既有測試：無。** 必須維持綠且不改：`tests/operations_doc_test.sh`（六標題、`abf-platform <word>` 存在、反引號路徑存在）、`tests/install_doc_test.sh`、`test_gcb_launch.py:1146-1170`、`test_gcb_ce.py:854-880`、`test_actions_layer.py:600-606`（PLATFORM「Action layer」小節 < 30 行）、`test_cloud_cost.py:772-790`、`tests/testing_web_doc_test.sh`。

## 完成標準（done when）
- T1–T9 全綠，T10 證據在 ledger；WSL `bash tests/run_all.sh` 綠。
- `git diff --name-only` 只含上列 5 個檔；沒有程式碼檔被改；新增測試 ≤ 15 條。
- PR 說明列出三處「以前／以後」文字與理由。

## 環境事實
- 測試在 WSL／Linux 跑；worktree 不可在同步磁碟（repo `CLAUDE.md`「For the executor and verifier」）。
- 文件測試只讀檔，不連網、不需要 Google 帳號。
- **前提檢查**：開工時若 `git grep "put_upload" origin/v3 -- platform` 有命中（byte-channel 已合併），T3 的 "not built yet" 句與 OPERATIONS 第 6 點要改成現況並回報 developer-agent，不要照本計畫寫。

## 不做
- 不寫 IAM 細節（前綴範圍的權限條件等）：本計畫查不到經核對的來源；要寫的話另開研究任務並附 Google 官方文件網址。
- 不改任何程式、不改 `docs/CLOUD.md`／`docs/INSTALL.md`、不新增文件檔。
- 不處理「價目表目前是空的」（`cloud-rates-fill` 的事）。
- 不需要 migration（無資料表或 JSON 內容改變）。

## 裁決
1. **為什麼放 OPERATIONS 而不是 CLOUD.md**：CLOUD.md 是中文的費用說明，且逐字被 `test_cloud_cost.py:772-790` 釘著；管理者操作類內容本來就在 OPERATIONS（`docs/OPERATIONS.md:215` 已有 Google Batch 小節）。
2. **為什麼等 `dataset-cli-launch`**：文件裡的指令必須真的存在（OPERATIONS 的測試會查 `abf-platform <word>`）；先寫會讓文件說謊。
3. **為什麼等 `resume-edit-params-d`**：它同改 `docs/PLATFORM.md`、`docs/TESTING.md`（`cloud-cleanup-f` 也是），同車道依序以免文件合併衝突。

## 裁決（2026-10-25，developer-agent）
1. 不寫 IAM 細節，明講「平台不授予也不檢查 bucket 權限」：接受。
2. 指令一律 `gcloud storage cp`（cloud-upload 裁決 3），不寫 gsutil。
3. 若 byte-channel 系列先合併，照計畫停下回報。

## 專長守則（docs）

（工作區沒有 `.claude/dev-profiles/docs.md`；本任務無專長守則。）
