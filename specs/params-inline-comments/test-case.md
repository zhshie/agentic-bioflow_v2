# 測試案例：params.yaml 行尾註解也算參數理由（params-inline-comments，issue #23）

<!--
Written by the verifier (CONTRACT mode) from `specs/params-inline-comments/plan.md`, 2026-10-25.
本任務沒有 spec.md；計畫就是規格（維護者指示：測試案例只取自計畫裡的範例 T1–T11，不另加行為）。
-->

**規格**：`specs/params-inline-comments/plan.md`（本任務無 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：不該被當成理由的寫法、或容易被誤判的寫法，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做、維持原狀。

名詞：「方法段」＝ `finish` 產生的方法說明文字；其中「Why these parameters」小節把 `params.yaml` 裡的註解（為什麼選這個值）跟著參數名稱列出來，格式是 `` - `參數名` — 理由 ``。「行尾註解」＝寫在參數同一行 `#` 後面的文字。

**共同做法（所有「自動」案例）**：測試在暫存資料夾寫一份 `params.yaml`，執行 `scripts/methods_text.py --assets … <run>/results`，只看輸出裡 `### Why these parameters` 之後的行。每個案例的 `params.yaml` 內容就是「前置條件」欄寫的那幾行，不多也不少。

## User Story 1 — 理由寫在哪都不會消失（優先度 P1）

維護者的要求（等價）：「理由寫在哪都不該消失」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | R1；計畫 T1 | 功能 | `params.yaml` 只有一行：`filter: true   # drop low quality on purpose`（理由寫在行尾，上方沒有註解） | 執行 methods_text 產生方法段 | 「Why these parameters」下出現 `` - `filter` — drop low quality on purpose ``。（目前版本這條整個消失，所以現在是紅的） | 自動：`tests/methods_text_test.sh` |
| TC-002 | R2；計畫 T2 | 功能 | `params.yaml` 兩行：第一行 `# reads are long`，第二行 `pacbio: true  # per the kit sheet`（上方有註解、行尾也有註解） | 同上 | 只出現**一條**：`` - `pacbio` — reads are long per the kit sheet ``（上方在前、行尾在後、中間一個空白；不是兩條） | 自動：`tests/methods_text_test.sh` |
| TC-003 | R3；計畫 T3 | 功能 | `params.yaml` 兩個連續的參數，各自有行尾註解：`a: 1  # first`、`b: 2  # second`，上方都沒有註解 | 同上 | 出現兩條，順序同檔案：`` - `a` — first `` 與 `` - `b` — second ``；`a` 那條不含 `second`，`b` 那條不含 `first` | 自動：`tests/methods_text_test.sh` |
| TC-004 | R3；計畫 T8 | 功能 | `params.yaml` 兩行：`a: 1 # one`，緊接 `b: 2`（`b` 上方沒有註解、行尾也沒有） | 同上 | 只有 `a` 一條（理由 `one`）；沒有 `b` 的條目，`one` 沒有跑到 `b` 身上 | 自動：`tests/methods_text_test.sh` |
| TC-005 | R4；計畫 T10 | 例外 | `params.yaml` 一行：`q: "say \"hi\" # not a comment"  # real`（雙引號值內有被跳脫的 `\"` 和一個 `#`，值後面才是真的行尾註解） | 同上 | `` - `q` — real ``；理由恰好是 `real`，不含 `say`、`hi`、`not a comment` | 自動：`tests/methods_text_test.sh` |
| TC-006 | R4；計畫 T4 | 例外 | `params.yaml` 一行：`url: http://x/y#frag`（`#` 前面不是空白，是網址的一部分） | 同上 | 沒有 `url` 的條目（網址片段不被當成註解） | 自動：`tests/methods_text_test.sh` |
| TC-007 | R4；計畫 T5（雙引號） | 例外 | `params.yaml` 一行：`msg: "a # b"` | 同上 | 沒有 `msg` 的條目（引號內的 `#` 不是註解） | 自動：`tests/methods_text_test.sh` |
| TC-008 | R4；計畫 T5（單引號） | 例外 | `params.yaml` 一行：`msg2: 'c # d'` | 同上 | 沒有 `msg2` 的條目 | 自動：`tests/methods_text_test.sh` |
| TC-009 | R5；計畫 T7（第一行） | 例外 | `params.yaml` 一行：`x: 1 #`（`#` 後面什麼都沒有） | 同上 | 沒有 `x` 的條目（空註解不算理由） | 自動：`tests/methods_text_test.sh` |
| TC-010 | R5；計畫 T7（第二行） | 例外 | `params.yaml` 一行：`y: 2 #   `（`#` 後面只有空白） | 同上 | 沒有 `y` 的條目 | 自動：`tests/methods_text_test.sh` |
| TC-011 | R6；計畫 T9 | 例外 | `params.yaml` 兩行：`  - item  # nested`（清單項目，沒有 `key:`），緊接 `b: 2` | 同上 | 沒有 `item` 的條目；輸出裡完全沒有 `nested`（它沒有被帶到後面的 `b`） | 自動：`tests/methods_text_test.sh` |

## User Story 2 — 既有寫法與範圍維持原狀（優先度 P1）

維護者的要求（等價）：「既有的上方註解寫法不能壞」；以及計畫「不做」「範圍」各項。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | R7；計畫 T6 | 功能 | 沿用 `tests/methods_text_test.sh` 既有的 `params.yaml`：`# Full-length reads, so the error model differs from the paired default.` 接 `pacbio: true`（只有上方註解） | 同上 | 輸出與改動前逐字相同：`` - `pacbio` — Full-length reads, so the error model differs from the paired default. ``；既有那條 `error model differs` 的斷言不改而綠 | 自動：`tests/methods_text_test.sh` |
| TC-013 | 計畫「不做」第 1 條、裁決；計畫 T11 | 不在範圍 | `params.yaml` 兩行：`#   trim_front: 5`（被註解掉的預設值），緊接 `outdir: results` | 同上 | 與改動前逐字相同：`` - `outdir` — trim_front: 5 ``（現況的瑕疵原樣保留；本次不修，只鎖住） | 自動：`tests/methods_text_test.sh` |
| TC-014 | 計畫「不做」第 3 條；R7 | 不在範圍 | 任一有理由的 `params.yaml` | 同上 | 小節標題 `### Why these parameters`、`Source: ` 那一行、`` - `參數名` — 理由 `` 的條目格式都和改動前一樣；`render()` 沒有被改 | 自動：`tests/methods_text_test.sh`、`tests/package_gaps_test.sh`（閱卷時另以 `git diff` 確認 `render()` 無變動） |
| TC-015 | 計畫「範圍：檔案」、完成標準 | 不在範圍 | 實作完成後 | 閱卷者執行 `git diff --name-only <base>...HEAD`；並比對 `tests/methods_text_test.sh` 與 base | 只出現 `scripts/methods_text.py`、`tests/methods_text_test.sh`、`specs/params-inline-comments/ledger.md` 三個檔；`collect_provenance.py`、`build_package.sh`、`hooks/`、`platform/`、`plugin.json`、憲法、`docs/` 都沒動；測試檔只**新增**案例（新增 ≤ 14 條），既有斷言沒有被改弱、刪除或跳過 | 自動：閱卷指令（`git diff`），不是測試檔 |
| TC-016 | 計畫「不做」第 1、2 條；作法 | 不在範圍 | 實作完成後 | 閱卷者讀 `scripts/methods_text.py` 的 diff | 改動只在 `rationale()` 與其上方一個私有輔助函式 `_split_inline`；沒有多行字串或 YAML 錨點的解析，也沒有嘗試分辨被註解掉的預設值；沒有新增資料表或 JSON 欄位（不需 migration） | 自動：閱卷指令（`git diff`），不是測試檔 |
| TC-017 | 完成標準 | 功能 | 計畫點名的五個既有測試檔 | 不改它們，各自執行 | `methods_text_test.sh`、`package_gaps_test.sh`、`build_package_test.sh`、`collect_provenance_test.sh`、`methods_text_fetch_test.sh` 全部通過，輸出 OK | 自動：這五個 `tests/*.sh` |
| TC-018 | 完成標準 | 功能 | 實作完成、工作樹乾淨 | 在 WSL 執行 `bash tests/run_all.sh` | 整套綠，沒有任何失敗 | 自動：`tests/run_all.sh` |

## 憲法與安全網

本任務動到「寫給使用者名下的方法段，必須指向產生它的檔案」（原則 IV，第 9 條）和「不得出現每條管線專屬的設定」（原則 I，第 1 條）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 第 9 條（來源要指向檔案） | 功能 | 有理由的 `params.yaml`（含行尾註解）已被收進方法段 | 看「Why these parameters」小節 | 標題下仍有 `` Source: `params.yaml` `` 那一行，且位於各理由條目之前（行尾註解帶進來的理由也標了來源）；`package_gaps_test.sh` 檢查「標題後三行含 `params.yaml`」不改而綠 | 自動：`tests/package_gaps_test.sh`、`tests/principle_9_test.sh` |
| TC-020 | 第 1 條（不寫每條管線的設定） | 功能 | 實作完成 | 執行 `tests/no_per_pipeline_config.sh` | 綠；`methods_text.py` 沒有出現管線名或工具名表，`rationale()` 只用標準函式庫 | 自動：`tests/no_per_pipeline_config.sh` |

<!--
Rules for the writer:
- 計畫 T1–T11 全數對應；T5、T7 各含兩個輸入，拆成兩列（一列一個預期）。
- IDs are never renumbered after approval.
-->
