---
id: samplesheet-output-dir
title: generate_samplesheet.py 的 -o 指到還不存在的資料夾時不再丟 Python traceback（文件寫的範例就是 -o metadata/samplesheet.csv）
tier: A
kinds: backend
lane: L-samplesheet-out
base: v3（`origin/v3` @ 50f696b；所有行號都是該版本）
source: developer-agent 讀碼查證＋實測（2026-10-25，WSL python3 實跑，見下）
---

# samplesheet-output-dir

> A 級 bug：樣本表產生器是 `launch` 流程的入口，第一次用的人 `metadata/` 還不存在，得到的是一整頁 traceback 加 exit 1，而 exit 1 在這支工具的定義裡是「沒找到樣本／驗證失敗」——訊息和結束碼都在說謊。純外掛側 Python，不碰 `platform/`、`hooks/`。

## 目標
`-o <路徑>` 的上層資料夾不存在時自動建立；建不起來或寫不進去時，印一行白話錯誤、exit 2、**什麼都不留下**，絕不丟 traceback。其餘行為（CSV 位元組、警告文字、結束碼 0／1／3）一字不變。

### 查證結果（皆 `origin/v3`）
- 寫檔處：`scripts/generate_samplesheet.py:216` `out = open(args.output, "w", newline="") if args.output else sys.stdout`——沒有 `makedirs`，也沒有 `try/except OSError`（後面的 `try/finally` 只管關檔，:217-224）。
- 文件寫的範例：檔頭用法 `scripts/generate_samplesheet.py:29-31` 是 `-o metadata/samplesheet.csv`；`skills/launch/SKILL.md:265-267` 要求叫它。
- 實測（WSL python3 3.10，輸入是兩個合法配對的 FASTQ，`-o <暫存>/nodir/sheet.csv`）：
  `FileNotFoundError: [Errno 2] No such file or directory: '<暫存>/nodir/sheet.csv'`，來源行 `generate_samplesheet.py:216`，`rc=1`。
- 結束碼的定義：`generate_samplesheet.py:33-35`「0 ok, 1 nothing found / validation failed, 2 bad usage…, 3 needs a decision」。所以現況的 `rc=1` 會被呼叫端當成「沒有樣本」。
- 驗證在前、開檔在後：`:190-199` 先 `build_rows`、`if not rows: … return 1`，所以失敗路徑本來就不會建檔——新建資料夾必須維持這個順序（`tests/generate_samplesheet_test.sh:42-50` `stopped()` 斷言「失敗時檔案不存在」）。
- 閘門：`hooks/confirm_walkthrough.sh:86,266` 把含 `generate_samplesheet` 的指令視為「寫樣本表」要求先走過 walkthrough；本任務**不改 hook**、也不改指令字樣，建資料夾發生在腳本內部。

## 維護者原話（verifier 出題用）
本任務沒有他的逐字裁示；來源是上面的實測。等價要求：
- 「文件範例照做就該成功」→ T1、T2。
- 「失敗要說人話、不要 traceback」→ T3、T4。
- 「失敗不留半成品」→ T5、T6。

## 範圍：檔案（只准改這些，共 3 個）
- `scripts/generate_samplesheet.py`（只改 :216 前後的寫檔段，與檔頭 :33-35 的結束碼說明一句）
- `tests/generate_samplesheet_test.sh`（只**加**案例，放在檔尾 `echo`／結論行之前；既有斷言一律不改）
- `specs/samplesheet-output-dir/ledger.md`（新）

**不准動**：`scripts/utils/*`、`scripts/prepare_launch.sh`、`hooks/`、`skills/`、`tests/fixtures/samplesheet_golden/*`、`platform/**`。

## 作法（決定）
1. 寫檔段改成：`out` 開檔前（且只在 `rows` 非空、所有警告已印之後）`os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)`；`open` 與 `makedirs` 一起包在 `try/except OSError as e`。
2. 失敗時 stderr 恰一行：`ERROR: cannot write <args.output 原樣>: <e.strerror>`，`return 2`；不印 traceback；不留下新建的空資料夾以外的任何東西（資料夾若是這次新建的，失敗時不必回收——見裁決）。
3. 成功時所有輸出（CSV 內容、警告、最後一行 `wrote N samples …`）**位元組不變**。
4. 檔頭結束碼說明改成 `2 bad usage (including no schema and no --roles, or an output path that cannot be written)`。
5. 不加 `--force`／不覆蓋保護——既有行為是覆蓋，維持。

## 失敗先行測試（`tests/generate_samplesheet_test.sh`，用現成的 `run`、`mkpairs`、`newout`、`$PAIRS`）
| # | 情境 | 期望 | 現在 |
|---|---|---|---|
| T1 | `-o $TMP/new/sub/sheet.csv`（兩層都不存在），配對輸入 `$PAIRS`，`--columns sample,fastq_1,fastq_2 --roles sample=sample,read1=fastq_1,read2=fastq_2` | RC 0；檔存在；首行 `sample,fastq_1,fastq_2`；3 列資料 | 紅（RC 1、traceback） |
| T2 | 同 T1 但 `cd` 到暫存目錄後用相對路徑 `-o metadata/samplesheet.csv` | RC 0；`metadata/samplesheet.csv` 存在 | 紅 |
| T3 | `-o $TMP/afile/sheet.csv`，其中 `afile` 是一般檔案 | RC 2；stderr 含 `ERROR: cannot write`；不含 `Traceback` | 紅 |
| T4 | T3 的 stderr 恰一行以 `ERROR: cannot write` 開頭，且帶出輸出路徑 | 如述 | 紅 |
| T5 | 需要決定：沿用 `tests/generate_samplesheet_test.sh:84-93` 的 TC-002 形狀（ampliseq schema、只要一組欄位），但 `-o $TMP/never/x.csv` | RC 3；`$TMP/never` **不存在** | 綠（鎖住順序） |
| T6 | 沒有樣本：輸入資料夾只有 R1、不給 `--single-end`（`mkdir -p "$TMP/solo" && : > "$TMP/solo/S1_R1_001.fastq.gz"`），`-o $TMP/never2/x.csv` | RC 1；`$TMP/never2` 不存在 | 綠（鎖住） |
| T7 | 上層資料夾已存在（既有所有案例的形狀） | 與現在逐字相同 | 綠（既有 TC-001 的 golden 即鎖住） |
| T8 | 不給 `-o`（stdout 模式） | RC 0；CSV 在 stdout；不建任何資料夾 | 綠（鎖住） |
| T9 | `-o` 的檔案已存在 | 被覆蓋（既有行為） | 綠（鎖住） |
| T10 | 成功時 stderr 最後一行仍是 `wrote 3 samples (3 paired, 0 single) -> <路徑>` | 如述 | 綠（鎖住） |

**現在會紅**：T1、T2、T3、T4。executor 先跑並貼出紅的輸出再動手；T1 在 base 上若是綠的，回報 BLOCKED。

**會改斷言的既有測試：無。** 已核對：`tests/generate_samplesheet_test.sh` 所有 `-o` 都指向既存的 `$TMP`（`newout` 用 `mktemp -u`，:39-40）；golden 的 `rnaseq.csv`、`rnaseq.stderr` 由 TC-001 逐位元比對（:68-79），成功路徑不變；`tests/confirm_walkthrough_test.sh` 只把 `generate_samplesheet.py` 當字串餵給 hook，不執行它。

## 完成標準（done when）
- T1–T10 全綠；`bash tests/generate_samplesheet_test.sh`、`tests/confirm_walkthrough_test.sh`、`tests/no_per_pipeline_config.sh`、`tests/path_shapes_test.sh` 不改而綠；整套 `bash tests/run_all.sh`（WSL）綠。
- `git diff --name-only` 只含上列 3 個檔；`hooks/` 零改動（證據貼進 ledger）。新增案例 ≤ 12 條。

## 環境事實
- 本計畫的失敗是實機重現的（上面的 `FileNotFoundError`），不是只讀碼推得。
- 測試以 `python3` 執行腳本（`tests/generate_samplesheet_test.sh:~34` `run()`）；原生 Windows 的 `python` 是 2.7，一律在 WSL 驗。
- 全套測試只能在 WSL 跑；worktree 不可在同步磁碟。

## 不做
- 不改配對邏輯、角色推斷、警告文字；不加新旗標；不改 `prepare_launch.sh` 自己產生的草稿路徑。
- 不需要 migration（無資料表、JSON 欄位）。

## 裁決
- **自動建資料夾，而不是只報錯**：文件範例 `-o metadata/samplesheet.csv` 的 `metadata/` 本來就是這個流程要建的資料夾；要求先 `mkdir` 等於要求呼叫端記得一個沒寫在任何地方的前置步驟。
- **建好資料夾後才開檔失敗，不回收那個空資料夾**：回收要判斷「是不是這次建的」，多一條會出錯的程式；空資料夾無害。
- **結束碼用 2**：沿用「用法／環境問題」的定義；1 專屬「沒有樣本」，不能混用。

## 裁決（2026-10-25 06:50，developer-agent）
1. 自動建立上層資料夾：接受。
2. 寫檔失敗用結束碼 2＋一行白話訊息（不印 traceback）：接受。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
