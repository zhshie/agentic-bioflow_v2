# 測試案例：settings-nano4（文件：nano4 設定鍵、站台對照表、兩條踩坑、公開網址一節）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. 繁體中文; identifiers and file paths stay as they are.
This is a docs-only task (kind: docs). There is no spec.md; the plan is the source. Every row comes from a sentence of the plan.
-->

**規格**：`specs/settings-nano4/plan.md`（這個任務沒有 spec.md，以計畫為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：不該被弄壞的東西，或會被現有測試抓到的情況。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

維護者原話對應：

- 「文件與驗收表：設定鍵、站台對照表、踩坑紀錄、實機驗收清單。」→ 設定鍵＝US1、站台對照表＝US2、踩坑紀錄＝US3；「實機驗收清單」屬 M1-07（`docs/TESTING.md`），計畫明列不做，見 TC-039。
- 「不另加任務，只在 M1-06 的 SETTINGS／OPERATIONS 補『公開網址』一節。」→ US4；「不另加任務」見 TC-040。
- 「試用成功＝同事不問我就能跑完一次 16S。」→ TC-010（文件要讓同事照做）。這句話本身要等 M1-07 和真機，本任務只能證明文件齊全且例子前後一致。

文件是英文的，下列「必須含」的字句，英文或對應中文都算。

## User Story 1 — 使用者照 `docs/SETTINGS.md` 把站台代理設成 nano4 模式（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法：`way_back` 鍵 | 功能 | 本任務完成後的 `docs/SETTINGS.md` | 讀 `way_back` 這一條 | 文件裡有 `way_back`，並寫明可選值是 `forward` 與 `direct` 兩個 | 自動：`tests/docs_nano4_keys.sh` |
| TC-002 | 作法：`way_back` 預設 | 功能 | 同上 | 讀 `way_back` 的預設值 | 寫明：當 `reach` 是 `ssh` 時預設為 `forward` | 自動：`tests/docs_nano4_keys.sh` |
| TC-003 | 作法：`direct` 需要 `platform_public_url` | 功能 | 同上 | 讀 `way_back` 的 `direct` 說明 | 寫明選 `direct` 就需要設定 `platform_public_url` | 自動：`tests/docs_nano4_keys.sh` |
| TC-004 | 作法：`platform_public_url` 鍵 | 功能 | 同上 | 讀 `platform_public_url` 這一條 | 文件裡有 `platform_public_url`，寫明它是 https 網址，並寫明 loopback（本機 127.0.0.1 之類）是例外、只給測試用 | 自動：`tests/docs_nano4_keys.sh` |
| TC-005 | 作法：`site_profile` 鍵 | 功能 | 同上 | 讀 `site_profile` 這一條 | 文件裡有 `site_profile`，寫明可選值是 `taiwania3` 與 `nano4`，用途是讓文件與預設值依站台分流 | 自動：`tests/docs_nano4_keys.sh` |
| TC-006 | 作法：`site_profile`「程式目前不讀，標保留」 | 功能 | 同上 | 讀 `site_profile` 這一條 | 明白標示「保留」（reserved），並寫明程式目前不讀這個鍵；沒有把它寫成會改變行為的設定 | 自動：`tests/docs_nano4_keys.sh` |
| TC-007 | 作法：三個站台鍵「各一行用途、型別、預設、例子」 | 功能 | 同上 | 逐一讀 `way_back`、`platform_public_url`、`site_profile` 三條 | 每一條都同時有：用途、型別（或可選值）、預設值、一個例子；缺任何一項即不合格 | 自動：`tests/docs_nano4_keys.sh` |
| TC-008 | 作法：CE 三個鍵 `modules`、`siteConfigVars`、`sitePipelines` | 功能 | 同上 | 讀這三個鍵的說明 | 三個鍵名都出現在 `docs/SETTINGS.md`，各有一句用途，並指向 `configs/sites/nchc-nano4-ce.json` 當範例（該檔由 L2 產生，這裡只要路徑寫對，檔案不必存在） | 自動：`tests/docs_nano4_keys.sh` |
| TC-009 | 完成標準：鍵名「一字不差」 | 功能 | 同上 | 逐字比對六個鍵名 | 六個鍵名的拼法與大小寫完全是：`way_back`、`platform_public_url`、`site_profile`、`modules`、`siteConfigVars`、`sitePipelines`（後兩個是駝峰，不是 `site_config_vars` 或 `site_pipelines`）；測試用整字比對，不接受近似拼法 | 自動：`tests/docs_nano4_keys.sh` |
| TC-010 | 維護者原話 17：「試用成功＝同事不問我就能跑完一次 16S。」→ 文件要讓同事照做 | 功能 | 一個只有 `docs/SETTINGS.md` 的讀者 | 照文件把 nano4 模式的三個站台鍵寫出來 | 光看文件就能寫出一組前後一致的設定：`way_back` 例子若是 `direct`，旁邊的例子就同時有 https 的 `platform_public_url`；不需要去問人，也沒有哪個值只出現名字、沒有例子 | 手動：驗收者逐字讀文件對照（本任務不新增 `docs/TESTING.md` 步驟，真機試用歸 M1-07） |
| TC-011 | 完成標準：不破壞既有內容 | 例外 | 本任務前的 `docs/SETTINGS.md` | 比對新舊檔 | 既有各節標題仍在（例如「The keys that cannot travel」「Keys this version does not read」「The token」「Migration」），既有內容沒有被刪減；`migration_doc_test.sh` 與其他引用 SETTINGS.md 的現有測試仍綠 | 自動：`tests/migration_doc_test.sh` 加比對 diff |

## User Story 2 — 維護者在 `docs/SITE_ADAPTER.md` 看出 nano4 與 Taiwania-3 在契約上的差別（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 作法：站台對照表加 nano4 一列 | 功能 | 本任務完成後的 `docs/SITE_ADAPTER.md` | 找 nano4 的對照 | 有一個明確標示 `nano4` 的列（或對照），與既有 Taiwania-3 並列可比；只出現在別處閒聊文字裡不算 | 自動：`tests/docs_nano4_keys.sh` |
| TC-013 | 作法：Resource | 功能 | 同上 | 讀 nano4 的 Resource | 寫明用國網的 `$NFCORE_SITE_CONFIG` 與 `selectQueue`，退路是 `configs/sites/nchc-nano4.config`（該檔由 L1 產生，這裡路徑寫對即可） | 自動：`tests/docs_nano4_keys.sh` |
| TC-014 | 作法：Egress | 功能 | 同上 | 讀 nano4 的 Egress | 寫明計算節點可直連外網、沒有 relay（不能沿用 Taiwania-3「計算節點無路出去、要 relay」的說法） | 自動：`tests/docs_nano4_keys.sh` |
| TC-015 | 作法：Reports | 功能 | 同上 | 讀 nano4 的 Reports | 寫明用 `-with-tower`，直接回報到 `platform_public_url` | 自動：`tests/docs_nano4_keys.sh` |
| TC-016 | 作法：Storage | 功能 | 同上 | 讀 nano4 的 Storage | 寫明是 `/work/u9613010` | 自動：`tests/docs_nano4_keys.sh` |
| TC-017 | 作法：Reach | 功能 | 同上 | 讀 nano4 的 Reach | 寫明 reach 是 `ssh`，兩段式驗證（2FA）由使用者自己開 ControlMaster（共用連線），Claude 不代開 | 自動：`tests/docs_nano4_keys.sh` |
| TC-018 | 作法：Identity | 功能 | 同上 | 讀 nano4 的 Identity | 寫明與 Taiwania-3（T3）相同 | 自動：`tests/docs_nano4_keys.sh` |
| TC-019 | 失敗先行測試：SITE_ADAPTER 必含 `NXF_SINGULARITY_LIBRARYDIR` | 功能 | 同上 | 搜尋這個變數名 | `docs/SITE_ADAPTER.md` 裡有 `NXF_SINGULARITY_LIBRARYDIR`，且是在 nano4 的說明脈絡中出現 | 自動：`tests/docs_nano4_keys.sh` |
| TC-020 | 完成標準：不破壞既有內容 | 例外 | 本任務前的 `docs/SITE_ADAPTER.md` | 比對新舊檔 | 既有 Taiwania-3 的表（Resource、Egress、Reports、Storage、Diagnosis、Reach、Drift check 各列）與六個契約標題原樣還在；`constitution_scope_test.sh`、`command_layer_is_site_neutral.sh` 仍綠 | 自動：`tests/constitution_scope_test.sh`、`tests/command_layer_is_site_neutral.sh` 加比對 diff |

## User Story 3 — 維護者在 `docs/PITFALLS.md` 看到兩條 nano4 踩坑（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | 作法：踩坑一（映像快取唯讀）之一 | 功能 | 本任務完成後的 `docs/PITFALLS.md` | 讀新增的「國網映像快取唯讀」那一條 | 標題或內文寫明國網的映像快取是唯讀的，並說明要用 `NXF_SINGULARITY_LIBRARYDIR` 去查（找現成映像） | 自動：`tests/docs_nano4_keys.sh` |
| TC-022 | 作法：踩坑一之二 | 功能 | 同上 | 讀同一條 | 寫明 `NXF_SINGULARITY_CACHEDIR` 要另外指向一個可寫的目錄（不是唯讀的那個），兩個變數的角色沒有混在一起 | 自動：`tests/docs_nano4_keys.sh` |
| TC-023 | 作法：踩坑二（本地 pipeline 路徑不可帶 `-r`） | 功能 | 同上 | 讀新增的「本地 pipeline 路徑」那一條 | 標題與內文寫明：pipeline 給的是本地路徑時，不可帶 `-r`（revision 參數） | 自動：`tests/docs_nano4_keys.sh` |
| TC-024 | 作法：「照該檔既有編號與格式」 | 功能 | 同上 | 看新增兩條的標題 | 兩條都用既有的粗體標題格式 `**N. 標題.**`，編號接在目前最大編號（51）之後，也就是 52 與 53，沒有與既有編號重複，也沒有改動任何舊條目的編號 | 自動：`tests/docs_nano4_keys.sh` |
| TC-025 | 完成標準：不破壞既有內容 | 例外 | 本任務前的 `docs/PITFALLS.md` | 比對新舊檔 | 既有條目 1 到 51 沒有被刪或改寫（只有在檔尾新增）；`pitfalls_supervise_test.sh` 與 `platform/tests/test_launch_docs.py` 仍綠 | 自動：`tests/pitfalls_supervise_test.sh` 加比對 diff |

## User Story 4 — 維護者與使用者在 `docs/OPERATIONS.md` 讀到「公開網址（進度回報）」一節（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-026 | 作法：加「公開網址（進度回報）」一節；維護者原話 11：「只在 M1-06 的 SETTINGS／OPERATIONS 補『公開網址』一節」 | 功能 | 本任務完成後的 `docs/OPERATIONS.md` | 找這一節的標題 | 有一個標題含「公開網址」或 `Public URL`（大小寫不拘），且只有這一節 | 自動：`tests/docs_nano4_keys.sh` 或新增的文件測試 |
| TC-027 | 作法：為什麼需要 https | 功能 | 同上 | 讀這一節 | 有一段講為什麼進度回報的網址需要 https | 自動：同上 |
| TC-028 | 作法：Tailscale Funnel 是其中一種做法，步驟指向維護者自己的筆記，不在此展開 | 功能 | 同上 | 讀這一節 | 提到 Tailscale Funnel，並明講它只是做法之一（不是唯一）；具體步驟只指向維護者自己的筆記，這一節沒有把設定步驟（指令、設定檔）展開寫出來 | 自動：同上 |
| TC-029 | 作法：`way_back: direct` 時站台怎麼驗 | 功能 | 同上 | 讀這一節的驗證方法 | 寫明：在站台上對 `https://<public>/user-info` 做 `curl`，應回 401，且回應帶 `X-ABF-Platform` | 自動：同上 |
| TC-030 | 完成標準：全套綠；現有 `operations_doc_test.sh` 不得被改動 | 例外 | 本任務完成後 | 不修改 `tests/operations_doc_test.sh`，直接執行它 | 仍然通過：恰好 6 個 `## ` 標題、第 6 個仍是 `Not built yet`、第 2 個仍含 Host 或 TLS；因此新的一節必須是 `###` 層級（或併入既有標題下），不能是第 7 個 `##`；該測試檔在 diff 裡沒有任何變動；這一節若用反引號寫 repo 路徑，該路徑必須真的存在（`configs/sites/nchc-nano4-ce.json`、`configs/sites/nchc-nano4.config` 目前不存在，所以不得用反引號寫在這裡） | 自動：`tests/operations_doc_test.sh` 加比對 diff |
| TC-031 | 作法：「OPERATIONS.md（只加『公開網址』一節）」 | 例外 | 同上 | 比對新舊 `docs/OPERATIONS.md` | diff 只有新增的這一節；原有各節（1 到 6）的文字沒有被改動、刪除或重排 | 自動：驗收者比對 diff |
| TC-032 | 一致性：OPERATIONS 第 6 節寫明 Funnel 與 proxy 設定「Not built yet」 | 例外 | 同上 | 讀新的一節與第 2、6 節 | 新的一節沒有宣稱本 repo 已經實作 Funnel／proxy 設定，也沒有與第 6 節「Nothing in this repository implements it」矛盾 | 自動：驗收者讀文件對照 |

## User Story 5 — 文件的一致性有機械檢查，而且先紅後綠（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-033 | 失敗先行測試：SETTINGS 必含六個鍵 | 功能 | `tests/` 底下新增 `docs_nano4_keys.sh`（或併入既有 docs 測試，由 executor 在 ledger 說明理由） | 執行該測試 | 檢查 `docs/SETTINGS.md` 含 `way_back`、`platform_public_url`、`site_profile`、`modules`、`siteConfigVars`、`sitePipelines` 六個鍵，任何一個缺就失敗並指出是哪一個 | 自動：`tests/docs_nano4_keys.sh` |
| TC-034 | 失敗先行測試：SITE_ADAPTER 與 PITFALLS | 功能 | 同上 | 執行該測試 | 檢查 `docs/SITE_ADAPTER.md` 有 `nano4` 列與 `NXF_SINGULARITY_LIBRARYDIR`，`docs/PITFALLS.md` 兩條新標題存在；缺任何一項就失敗 | 自動：`tests/docs_nano4_keys.sh` |
| TC-035 | 「先寫、現在會紅」 | 功能 | 本任務開始前的 base 文件（沒有任何本任務的文件修改） | 在 base 的文件上執行新測試 | 測試失敗（紅），而且是因為鍵或條目缺失而失敗，不是因為檔案不存在或語法錯誤；加上文件修改後才轉綠 | 自動：驗收者在 base 文件上跑一次（或對照 ledger 的紅燈紀錄） |
| TC-036 | 完成標準：新測試綠，並被全套收進去 | 功能 | 同上 | 看 `tests/` 與 `tests/run_all.sh` 的行為 | 新測試檔跟同目錄其他測試一樣可執行，會被 `run_all.sh` 自動找到並執行，計入最後的總數 | 自動：`tests/run_all.sh` |
| TC-037 | 完成標準：全套綠 | 功能 | 本任務完成、HEAD 乾淨 | 在 WSL 或 Linux 跑 `tests/run_all.sh` | 全部通過；`executor-status` 為 `GREEN <HEAD sha>` | 自動：`tests/run_all.sh` |

## 範圍邊界（計畫「不做」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-038 | 不做：不改 `README.md`、ADR、ROADMAP（M1-08，C 級，維護者合併） | 不在範圍 | 本任務完成後 | 比對相對於 base 的變更檔案 | `README.md`、`docs/adr/` 底下任何檔、`docs/ROADMAP.md` 都沒有被改 | 自動：驗收者看 `git diff --stat` |
| TC-039 | 不做：不改 `docs/TESTING.md`（M1-07）；「實機驗收清單」不在本任務 | 不在範圍 | 同上 | 比對 | `docs/TESTING.md` 沒有任何變動，沒有偷偷加上 nano4 實機驗收步驟 | 自動：驗收者看 `git diff --stat` |
| TC-040 | 範圍：只有四份文件；維護者原話 11「不另加任務」；CE 範例檔「由 L2 產生，文件先寫路徑」 | 不在範圍 | 同上 | 比對變更檔案 | 變更只限 `docs/SETTINGS.md`、`docs/SITE_ADAPTER.md`、`docs/PITFALLS.md`、`docs/OPERATIONS.md`、新增的那個測試，以及 `specs/settings-nano4/` 底下的紀錄；`scripts/`、`platform/`、`hooks/`、`configs/` 都沒動；`configs/sites/nchc-nano4-ce.json`、`configs/sites/nchc-nano4.config` 沒有被這個任務建立；沒有任何程式開始讀 `site_profile` | 自動：驗收者看 `git diff --stat` 並 grep 程式碼 |
| TC-041 | 環境事實：「本任務不連真機」 | 不在範圍 | 同上 | 檢查新測試與 ledger | 新測試只對檔案文字做 grep 比對，沒有 `ssh`、`curl` 到站台、`sbatch` 或任何網路動作；ledger 沒有記載連過真機 | 自動：驗收者讀測試檔 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-042 | 第 8 條（先量或讀原始碼才下斷言，結果記在 `docs/PITFALLS.md`；檢查＝每條踩坑對應一次真實失敗或一次真實讀源碼） | 功能 | 本任務完成後的 `docs/PITFALLS.md` | 讀新增的兩條 | 兩條都像既有條目一樣寫明「看到了什麼」以及在哪裡量到或讀到（站台、日期、指令或來源檔其中至少一項），不是只丟一條沒有出處的規則；查不到出處的條目，驗收列 UNVERIFIED | 手動：驗收者讀兩條對照 ledger 與計畫的環境事實 |
| TC-043 | 安全網範圍（`tests/constitution_scope_test.sh` 禁止 SITE_ADAPTER.md 把安全網寫成無條件、永遠開著） | 例外 | 同上 | 執行 `tests/constitution_scope_test.sh` | 通過；新增的 nano4 文字沒有「every session／always on／unconditional」之類的說法，且原有的 `Constitution 2.0.0` 字樣仍在 `docs/SITE_ADAPTER.md` | 自動：`tests/constitution_scope_test.sh` |

<!--
IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
