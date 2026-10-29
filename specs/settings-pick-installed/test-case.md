# 測試案例：設定頁登記管線改成「從站台已安裝清單挑選」；雲端不顯示登記（settings-pick-installed）

<!--
Written by the verifier (CONTRACT mode) from specs/settings-pick-installed/plan.md, DESIGN.md, PRODUCT.md and the sibling contract specs/settings-register-pipeline/ (whose TCs stay in force for the advanced form). No spec.md exists for this task: the plan is the spec.
Reader: the maintainer (not an engineer). Language: 繁體中文; identifiers, paths, routes, notice keys stay as they are.
-->

**規格**：`specs/settings-pick-installed/plan.md`（本任務沒有 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞（一句話）：
- **站台**：使用者自己租的伺服器或國網帳號（叢集，slurm 類型）。**雲端類型**：Google Batch、AWS、Azure（`compute_envs.PLATFORM_HOST_TYPES`）。
- **站台盤點**：預檢時順便用只讀指令問站台「`module` 裡裝了哪些 nf-core 管線版本」，結果放在預檢回傳的獨立欄位 `site_inventory`。
- **清單狀態**：`ok`（讀到了）、`no_module_system`（站台沒有 module 指令）、`error`（讀取失敗）、`none`（平台還沒收到任何含盤點的預檢）。
- **挑選（pick）**：網頁下拉選一項，送出的值是「管線 版本」，例如 `nf-core/ampliseq 2.18.0`；模組名稱與資料夾變數由伺服器從最新清單查出，不信任瀏覽器送來的值。
- **進階：手動填寫**：#259 原本的四格表單（管線、版本、模組名稱、管線資料夾變數），收在可收合區塊內，行為不變。
- **確認頁／CSRF 權杖／預檢**：同 `specs/settings-register-pipeline/test-case.md` 的名詞。
- 測試檔縮寫：`S` ＝ `platform/tests/test_station_site_inventory.py`（或併入既有站台預檢測試檔，ledger 註明）；`T` ＝ `platform/tests/test_settings_pick_installed.py`。「ann」「ben」是兩位不同使用者；「ann-ce」是 ann 名下的 slurm 運算環境；「ann-gcb」是 ann 名下的雲端環境。
- 範例資料取自計畫：模組 `biology/nf-core-ampliseq/2.18.0`（變數 `NFCORE_AMPLISEQ_HOME`，由 `module show` 讀到）、`biology/nf-core-rnaseq/3.14.0`（`module show` 沒有變數，推算為 `NFCORE_RNASEQ_HOME`）、`biology/Nextflow/26.10.0`（非 nf-core）、`foo/nf-core-bad;rm/1`（含危險字元）。

## 出題者訂定的字串（計畫裁決 4：計畫未寫的字串由 verifier 依既有慣例訂）

計畫已寫的句子逐字照用；以下是計畫沒寫、由出題者訂的預期值（TC 用到時標「訂定」）。

| 用途 | 中文 | 英文 |
|---|---|---|
| 通知 `inv_queued`（訂定） | ✓ 已排入讀取站台清單。 | ✓ Reading the site list has been queued. |
| 通知 `inv_no_agent`（訂定） | ○ 站台代理目前離線，未能讀取站台清單。 | ○ The site agent is offline; the site list could not be read. |
| 雲端環境一句（計畫給中文） | 此環境每次送出都直接取用 nf-core 官方版本，不需登記管線。 | This environment uses the nf-core release directly on every run; no pipeline registration is needed. |
| 下拉標籤（計畫給中文） | 站台已安裝的管線版本 | Pipeline version installed on the site |
| 推算後綴（計畫給中文） | （變數名稱為推算） | (variable name is inferred) |
| 讀取時間灰字（計畫給中文） | 清單讀取於 <時間> | List read at <time> |
| 按鈕（計畫給中文） | 重新讀取站台清單 | Reload site list |
| `none` 狀態（計畫給中文） | 尚未讀取此站台已安裝的管線。 | The pipelines installed on this site have not been read yet. |
| `no_module_system`／清單空（計畫給中文） | 此站台沒有找到已安裝的 nf-core 模組：送出時直接取用 nf-core 官方版本。若管線裝在模組以外的位置，請使用下方「進階：手動填寫」。 | No installed nf-core modules were found on this site: runs use the nf-core release directly. If the pipeline is installed outside the modules, use "Advanced: fill in manually" below. |
| `error` 狀態（計畫給中文） | ✕ 未能讀取站台清單：<原因> | ✕ Could not read the site list: <reason> |
| 進階區標題（計畫給中文） | 進階：手動填寫（管理者用） | Advanced: fill in manually (administrators) |
| `pick` 不在清單的 400（計畫給中文） | 站台清單中沒有這個版本，請按「重新讀取站台清單」。 | This version is not in the site list. Press "Reload site list". |

## 維護者原話對照

| 原話 | 對應 TC |
|---|---|
| 原話 1「我不太清楚登記管線哪邊o不ok，不知道怎麼填」（10-29）→ 一般人不必知道模組名稱與環境變數就能完成登記 | E01、D06、B01、B11、M03 |
| 原話 2「同意，而且nano4有裝好管線的情況與自己租的伺服器狀況也不一樣」（10-29）→ 叢集與雲端分開處理；叢集沒有模組系統或沒裝任何 nf-core 模組時說清楚並照常可送出 | D01、D08、D09、E02、E03、S04、S07 |
| 原話 3「登記管線要做，畢竟是裝在使用者自己租的伺服器或國網。」（10-28，仍適用） | E04、D03、D12、B11 |
| 原話 4「先把功能做起來吧，以後再改美觀」（10-23，仍適用） | D19、X06（只用既有 class，樣式表不變） |
| DESIGN 原話 7「介面上不要有AI太口語化的回覆，要有制式化的通知呈現」 | R08、D20、D15 |
| DESIGN 原話 5「做成產品英文版面是必須的」 | D13、D14、R08 |
| DESIGN 原話 13（按鈕只用固定動詞，不放數字與檔名） | D16 |

## 1. 站台盤點（作法 1；測試檔 S；用假站台，不連真站台）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| S01 | 作法 1；失敗先行測試（站台） | 功能 | slurm 環境；假站台 `connect` 通過；`module -t avail` 輸出含 `biology/nf-core-ampliseq/2.18.0`、`biology/nf-core-rnaseq/3.14.0`、`biology/Nextflow/26.10.0`、`foo/nf-core-bad;rm/1` | 執行 preflight | 回傳含獨立欄位 `site_inventory`，`status` 為 `ok`；`items` 恰好兩筆（ampliseq、rnaseq），Nextflow 與含 `;rm` 的那筆不在；每筆有 `pipeline`、`revision`、`module`、`home`、`home_source` 五個欄位；ampliseq 那筆為 `pipeline="nf-core/ampliseq"`、`revision="2.18.0"`、`module="biology/nf-core-ampliseq/2.18.0"`；rnaseq 那筆為 `nf-core/rnaseq`、`3.14.0` | 自動：`S` |
| S02 | 作法 1（module show 有變數） | 功能 | 同 S01；`module show biology/nf-core-ampliseq/2.18.0` 輸出含 `setenv NFCORE_AMPLISEQ_HOME`（及其他不相關的 setenv 行） | 執行 preflight | ampliseq 那筆 `home="NFCORE_AMPLISEQ_HOME"`、`home_source="module"` | 自動：`S` |
| S03 | 作法 1（推算規則） | 功能 | 同 S01；`module show biology/nf-core-rnaseq/3.14.0` 輸出沒有 `NFCORE_..._HOME` 變數 | 執行 preflight | rnaseq 那筆 `home="NFCORE_RNASEQ_HOME"`、`home_source="guessed"`（規則：`NFCORE_` ＋ 名稱轉大寫、`-` 換 `_` ＋ `_HOME`）；另以名稱含 `-` 的模組（例 `nf-core-sarek`、`nf-core-scrna-seq`）驗證 `-` 換成 `_` | 自動：`S` |
| S04 | 作法 1；原話 2（沒有模組系統） | 例外 | 假站台對 `module` 回 `module: command not found` | 執行 preflight | `site_inventory` 為 `{"status": "no_module_system", "items": [], ...}`；沒有丟出未處理的例外 | 自動：`S` |
| S05 | 作法 1（status=error） | 例外 | 假站台的 `module -t avail` 以非「找不到指令」的原因失敗（例如連線中斷、逾時、非零結束碼加其他錯誤文字） | 執行 preflight | `site_inventory.status` 為 `error`，`items` 為 `[]`；沒有未處理的例外 | 自動：`S` |
| S06 | 作法 1（獨立欄位；不影響通過與否） | 功能 | 同一個假站台、同一個環境設定，分別讓盤點為 `ok`、`no_module_system`、`error`、與（用替身拿掉盤點步驟的）base 行為 | 各執行一次 preflight，比對 `ok`、`checks`（名稱、狀態、細節）、`message` | 四次的 `ok`、`checks`、`message` 完全相同；`site_inventory` 不在 `checks` 清單裡（`checks` 中沒有任何名稱含 inventory 的項目） | 自動：`S` |
| S07 | 作法 1（雲端不跑盤點） | 功能 | 三種雲端環境（Google Batch、AWS、Azure）各一，用各自的預檢替身 | 各執行一次預檢 | 回傳不含 `site_inventory` 欄位；沒有對站台發出任何 `module` 指令 | 自動：`S` |
| S08 | 作法 1（指令固定，不含使用者輸入） | 功能 | 兩個內容不同的 slurm 環境設定，`name`、`modules`、`workDir`、`siteConfigVars`、`sitePipelines`、說明都塞入獨特標記字串 | 執行 preflight，攔截盤點送出的指令字串 | 指令字串在兩個環境之間完全相同；字串中不含任何來自環境設定的標記值 | 自動：`S` |
| S09 | 作法 1（只讀） | 功能 | 攔截盤點指令（同一次 ssh 呼叫） | 檢查指令 | 一次 ssh 呼叫完成；含 `module -t avail` 與 `module show`；不含 `module load`、安裝、刪除、`rm`、`>` 寫入導向或其他會改動站台的動作 | 自動：`S` |
| S10 | 作法 1（每筆先過同一套欄位驗證，過不了的丟掉） | 例外 | `module -t avail` 含符合名稱格式但過不了驗證的兩筆：`biology/nf-core-foo/main`（版本是分支名）、`biology/nf-core-` 加 70 個合法字元再接 `/1.0`（管線名超過 64 字元）；另有合法的 ampliseq | 執行 preflight | 兩筆壞的被丟掉、合法的 ampliseq 仍在；`status` 仍為 `ok`（不是整份失敗） | 自動：`S` |
| S11 | 作法 1（最多 200 筆） | 功能 | `module -t avail` 含 250 筆合法的 nf-core 模組 | 執行 preflight | `items` 不超過 200 筆；preflight 不出錯 | 自動：`S` |
| S12 | 作法 1（connect 通過後才盤點） | 例外 | 假站台 `connect` 失敗 | 執行 preflight | 回傳沒有 `site_inventory` 欄位（或盤點不被執行）；沒有任何 `module` 指令送到站台；verdict 與 base 的 connect 失敗相同 | 自動：`S` |
| S13 | 作法 1（read_at） | 功能 | 盤點成功 | 讀 `site_inventory` | 有非空的 `read_at`（時間）；`no_module_system` 與 `error` 也有 | 自動：`S` |
| S14 | 環境事實（`module avail` 輸出很長，只看前 100 行會漏） | 功能 | `module -t avail` 先輸出 300 行不相干的模組，之後才出現 `biology/nf-core-ampliseq/2.18.0` | 執行 preflight | ampliseq 那筆仍被讀到 | 自動：`S` |
| S15 | 作法 1（名稱格式 `(^|/)nf-core-…/版本$`） | 功能 | `module -t avail` 含沒有前綴資料夾的 `nf-core-atacseq/2.1.2`，與有前綴的 `biology/nf-core-atacseq/2.1.2` | 執行 preflight | 兩者的名稱格式都符合，各自成一筆，`pipeline` 皆為 `nf-core/atacseq`、`revision` 皆為 `2.1.2` | 自動：`S` |

## 2. 動作層：讀站台清單與傳遞（作法 2、5；測試檔 T）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| A01 | 作法 2（最近一次） | 功能 | ann-ce 有兩個已完成的預檢結果，先後含不同的 `site_inventory` | 以 `caller=ann` 呼叫 `site_pipeline_inventory` | 回傳較新那一次的清單（狀態、項目、`read_at`） | 自動：`T` |
| A02 | 作法 2（沒有＝none） | 例外 | ann-ce 從未有含 `site_inventory` 的預檢 | 呼叫 `site_pipeline_inventory` | 回 `{"status": "none"}` | 自動：`T` |
| A03 | 作法 2（最近一次「有 site_inventory」的） | 功能 | ann-ce 先有含清單的預檢，之後一次預檢在 connect 就失敗（沒有 `site_inventory`） | 呼叫 `site_pipeline_inventory` | 回傳較早那次含清單的結果，不是 `none` | 自動：`T` |
| A04 | 作法 2；backend 守則（跨使用者讀） | 例外 | ben 擁有 ben-ce 且有清單；ann 為呼叫者 | ann 以 `caller=ann` 查 ben-ce；另查一個不存在的環境名稱 | 兩者回應完全相同（找不到）；回應不含 ben-ce 的任何項目 | 自動：`T` |
| A05 | 作法 2（只讀） | 功能 | ann-ce 有清單，記下資料庫全部內容 | 呼叫 `site_pipeline_inventory`（不提供 `confirmed_by`） | 可呼叫、不需人工確認管道；呼叫前後資料庫（含工作佇列、更新時間）逐位元相同 | 自動：`T` |
| A06 | 作法 1＋2（結果經平台入庫仍在；防空殼） | 功能 | 模擬站台代理對 ann-ce 的 preflight 工作回報含 `site_inventory`（`ok`、兩筆項目、`read_at`）的結果，走平台真正的收結果路徑（`jobs` 的收結果處理） | 回報後呼叫 `site_pipeline_inventory` | 回傳與回報相同的狀態與兩筆項目（五個欄位、`read_at`）；不是 `none` | 自動：`T` |
| A07 | 作法 2（module／home 由呼叫端傳入的方式保留） | 功能 | ann-ce 登記清單為空 | 以 `confirmed_by=PAGE`、`caller=ann` 呼叫 `register_site_pipeline`，直接傳 module 與 home | 與 #259 相同：寫入一筆、四值與送入相同、排一次預檢；#259 動作層 TC（A01–A20）對應的既有測試維持綠 | 自動：`T` 與既有 `platform/tests/test_web_settings_register.py` |

## 3. 網頁「挑選」登記：`POST /settings/pipelines` 帶 `pick`（作法 2；測試檔 T）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| B01 | 作法 2；原話 1 | 功能 | ann 已登入；ann-ce 最新清單 `ok`，含 `nf-core/ampliseq 2.18.0`（module `biology/nf-core-ampliseq/2.18.0`、home `NFCORE_AMPLISEQ_HOME`）；記下資料庫 | ann 送出 `op=add`、`ce=ann-ce`、`pick=nf-core/ampliseq 2.18.0` 與正確 CSRF（不送 module、home） | 回 200 確認頁，列出六項：動作（新增）、環境、管線 `nf-core/ampliseq`、版本 `2.18.0`、模組名稱 `biology/nf-core-ampliseq/2.18.0`、管線資料夾變數 `NFCORE_AMPLISEQ_HOME`；資料庫與工作佇列完全沒有改變 | 自動：`T` |
| B02 | 作法 2（沿用 #259 確認頁） | 功能 | 取得 B01 的確認頁 | 檢查頁面表單 | 與 #259 確認頁結構相同：表單送往 `/settings/pipelines/confirm`；六個欄位以 hidden 帶回（module、home 為伺服器查出的值）；確認用 CSRF 綁定（op、ce、pipeline、revision、module、home）的雜湊；有「確認」按鈕；「返回」是連到 `/settings` 的連結 | 自動：`T` |
| B03 | 作法 2（不信任瀏覽器送來的 module／home）；失敗先行測試 | 例外 | 同 B01 | 送出 `pick=nf-core/ampliseq 2.18.0` 並夾帶 `module=evil`、`home=EVIL_HOME` | 確認頁顯示的 module／home 仍是伺服器查出的 `biology/nf-core-ampliseq/2.18.0` 與 `NFCORE_AMPLISEQ_HOME`；頁面任何位置（含 hidden 欄位）都找不到 `evil`、`EVIL_HOME`；資料庫不變 | 自動：`T` |
| B04 | 作法 2（pick 不在清單＝400） | 例外 | 同 B01；清單中沒有 `nf-core/ampliseq 9.9.9` | 送出 `pick=nf-core/ampliseq 9.9.9` | 回 400；訊息為「站台清單中沒有這個版本，請按「重新讀取站台清單」。」（`?lang=en` 為訂定的英文句）；顯示在 ann-ce 那一列上方並有 `✕` 符號；不顯示確認頁；資料庫不變、不排工作 | 自動：`T` |
| B05 | 作法 2（清單 none／no_module_system／error 時 pick 也不成立） | 例外 | ann-ce 清單分別為 `none`、`no_module_system`、`error`、`ok` 但 `items` 空 | 各送出 `pick=nf-core/ampliseq 2.18.0` | 四次都與 B04 相同：400、同一句、不寫入 | 自動：`T` |
| B06 | 作法 2（pick＝pipeline＋空白＋revision） | 例外 | 同 B01 | 分別送出 `pick` 為：空字串、缺欄位、`nf-core/ampliseq`（無版本）、`nf-core/ampliseq  2.18.0`（兩個空白）、`nf-core/ampliseq 2.18.0 extra`、`nf-core/ampliseq\n2.18.0` | 每次都是 400、不顯示確認頁、資料庫不變、不洩漏內部資訊；格式不合者不會被當成清單中的那一筆放行 | 自動：`T` |
| B07 | 作法 1＋2（推算的變數） | 功能 | 清單中 `nf-core/rnaseq 3.14.0` 的 `home_source="guessed"`、home 為 `NFCORE_RNASEQ_HOME` | 送出 `pick=nf-core/rnaseq 3.14.0` | 確認頁的管線資料夾變數為 `NFCORE_RNASEQ_HOME`（伺服器查出的值） | 自動：`T` |
| B08 | 作法 3（雲端不登記）；作法 2 | 例外 | ann 有雲端環境 ann-gcb（沒有站台清單） | 對 ann-gcb 送出 `op=add` 與 `pick=nf-core/ampliseq 2.18.0` | 與 B04 相同：400、同一句、不寫入 | 自動：`T` |
| B09 | 作法 2；backend 守則（跨使用者） | 例外 | ben 擁有 ben-ce 且有含 `nf-core/ampliseq 2.18.0` 的清單；ann 已登入 | ann 送出 `ce=ben-ce`、`pick=nf-core/ampliseq 2.18.0`；另送不存在的環境名稱 | 兩者回應相同（400、環境找不到的錯誤句，顯示在頁首）；頁面不出現 ben-ce 的任何資料；ben-ce 不變 | 自動：`T` |
| B10 | 作法 2（CSRF、來源、登入、臨時密碼同 #259） | 例外 | ann 已登入；備有 `pick` 表單 | 分別送出：缺 CSRF、錯 CSRF、別用途的 CSRF、別的來源（Origin／Referer）、未登入、臨時密碼未改 | 前四種回 403，不顯示確認頁、不寫入；未登入回 303 到 `/login`；臨時密碼回 303 到 `/welcome` | 自動：`T` |
| B11 | 作法 2、3；原話 1、3 | 功能 | ann-ce 代理在線、清單 `ok` 含 ampliseq；登記清單為空 | ann 走完兩步：B01 的確認頁按「確認」 | 回 303，位置為 `/settings?notice=added_queued&ce=ann-ce#ce-ann-ce`；ann-ce 的 `sitePipelines` 恰好多一筆 `{pipeline:"nf-core/ampliseq", revision:"2.18.0", module:"biology/nf-core-ampliseq/2.18.0", home:"NFCORE_AMPLISEQ_HOME"}`；佇列新增恰好一筆預檢；ann-ce 其他設定不變 | 自動：`T` |
| B12 | 作法 2（第二步只信雜湊綁定的欄位） | 例外 | 取得 B01 的確認頁與確認用 CSRF | 第二步送出時把 hidden 的 module 或 home 改成別的值 | 回 403，資料庫不變 | 自動：`T` |
| B13 | 作法 3（進階手填行為不變）；#259 | 功能 | ann-ce；不帶 `pick`，帶四格欄位（pipeline、revision、module、home）與 `op=add` | 送出 | 與 #259 完全相同：回 200 確認頁，module／home 取自送入的欄位；#259 的欄位驗證錯誤（module 含 `..`、home 小寫、revision 為分支名、非 nf-core）仍回 400、錯誤句不變、已填值保留；`op=remove` 仍可用 | 自動：`T` 與既有 `test_web_settings_register.py` |
| B14 | 作法 2（必填） | 例外 | ann-ce | 送出 `op=add` 但 `pick` 與四格欄位都沒有 | 回 400，不顯示確認頁，資料庫不變，錯誤句指出缺哪一欄 | 自動：`T` |

## 4. 「重新讀取站台清單」（作法 2；測試檔 T）

按鈕所屬表單的 action 即為此路由（計畫未訂路徑，TC 不釘路徑）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| R01 | 作法 2 | 功能 | ann-ce 代理在線；記下資料庫 | ann 按「重新讀取站台清單」（送出該表單與正確 CSRF） | 回 303，位置含 `notice=inv_queued` 與 `ce=ann-ce`、錨點 `#ce-ann-ce`；佇列恰好新增一筆 ann-ce 的預檢工作；跟隨後該列上方顯示「✓ 已排入讀取站台清單。」 | 自動：`T` |
| R02 | 作法 2（離線） | 功能 | ann-ce 的站台代理離線或沒有代理 | 按「重新讀取站台清單」 | 303，`notice=inv_no_agent`；沒有新增工作；顯示「○ 站台代理目前離線，未能讀取站台清單。」；不拋錯 | 自動：`T` |
| R03 | 作法 2（CSRF） | 例外 | ann 已登入 | 分別送出：缺 CSRF、錯 CSRF、別用途的 CSRF（例如登出用、或 `pick` 登記用） | 每次回 403；沒有新增工作；403 頁說明表單失效、什麼都沒有改、請重新整理後再試 | 自動：`T` |
| R04 | 作法 2（same-origin） | 例外 | ann 已登入，備有正確 CSRF | 以別的來源送出 | 回 403；沒有新增工作 | 自動：`T` |
| R05 | 作法 2（登入） | 例外 | 未登入；臨時密碼未改 | 各送出一次 | 未登入回 303 到 `/login`；臨時密碼回 303 到 `/welcome`；都沒有新增工作 | 自動：`T` |
| R06 | 作法 2；backend 守則（跨使用者寫） | 例外 | ben 擁有 ben-ce；ann 已登入 | ann 對 ben-ce 送出重新讀取；另對不存在的環境送出 | 兩者回應相同（找不到）；ben-ce 沒有新增工作 | 自動：`T` |
| R07 | 作法 2（不需確認頁、只寫 jobs） | 功能 | ann-ce 有設定與登記，記下資料庫 | 按「重新讀取站台清單」 | 一次 POST 就完成（沒有確認頁）；資料庫只差一筆新的預檢工作；ann-ce 的 `sitePipelines`、`modules`、`siteConfigVars` 等設定不變 | 自動：`T` |
| R08 | 作法 2、4（通知字串）；DESIGN 原話 7、5 | 功能 | ann 已登入，有 ann-ce | 開 `/settings?notice=inv_queued&ce=ann-ce` 與 `notice=inv_no_agent`；中英各一次；另開 `notice=bogus`、`notice=<script>x</script>` | 通知出現在 ann-ce 那一列上方，句首符號後接文字，內容為「出題者訂定的字串」表中的中英句；`bogus`、`<script>` 不顯示任何通知且不被原樣印出 | 自動：`T` |

## 5. 設定頁畫面（作法 3、4；DESIGN.md；測試檔 T）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| D01 | 作法 3（雲端）；原話 2 | 功能 | ann 有三種雲端環境各一（Google Batch、AWS、Azure），資料庫中都沒有 `sitePipelines` | 開 `/settings` | 每個雲端環境區塊只有一句「此環境每次送出都直接取用 nf-core 官方版本，不需登記管線。」（`?lang=en` 為訂定的英文句）；區塊內沒有登記表單、沒有下拉、沒有「重新讀取站台清單」按鈕、沒有「進階：手動填寫」 | 自動：`T` |
| D02 | 作法 3（雲端意外有登記照列） | 例外 | 雲端環境 ann-gcb 的資料庫資料中意外有兩筆 `sitePipelines` | 開 `/settings` | 兩筆照列，各有「移除」小表單（送往 `/settings/pipelines`、`op=remove`）；仍有 D01 那一句；沒有登記表單、下拉、重新讀取按鈕 | 自動：`T` |
| D03 | 作法 3（slurm ok 有項目）；原話 3 | 功能 | ann-ce 清單 `ok`，項目為 ampliseq 2.18.0、rnaseq 3.14.0；登記清單為空 | 開 `/settings` | 「登記管線」區有一個必填（`required`）下拉，標籤「站台已安裝的管線版本」；選項文字逐字為 `nf-core/ampliseq 2.18.0`、`nf-core/rnaseq 3.14.0`；選項的值能讓伺服器還原成 pipeline＋revision（即 `pick`）；表單送往 `/settings/pipelines`、`op=add`；已登記清單仍在（同 #259） | 自動：`T` |
| D04 | 作法 3（已登記的不列） | 功能 | 同 D03，但 ann-ce 已登記 `nf-core/ampliseq 2.18.0` | 開 `/settings` | 下拉只有 `nf-core/rnaseq 3.14.0`；不含 `nf-core/ampliseq 2.18.0`；以「管線＋版本」判斷（已登記 ampliseq 2.17.0 時，2.18.0 仍列出） | 自動：`T` |
| D05 | 作法 3（推算標註） | 功能 | 同 D03，rnaseq 的 `home_source="guessed"`、ampliseq 為 `module` | 開 `/settings` | rnaseq 的選項文字結尾為「（變數名稱為推算）」；ampliseq 的選項沒有這個後綴 | 自動：`T` |
| D06 | 作法 3；原話 1（人只選版本） | 功能 | 同 D03 | 檢查 `<details>` 以外、登記區內的所有輸入欄位 | 除了 CSRF 與 hidden 的 `op`、`ce` 外，可輸入或可選的欄位只有那一個下拉；沒有任何模組名稱或管線資料夾變數的文字輸入、也沒有它們的標籤；灰字「清單讀取於 <時間>」（時間取自清單的 `read_at`）、按鈕「重新讀取站台清單」、按鈕「登記」都在 | 自動：`T` |
| D07 | 作法 3（none） | 功能 | ann-ce 從未讀過清單（`none`） | 開 `/settings` | 顯示「尚未讀取此站台已安裝的管線。」與按鈕「重新讀取站台清單」；沒有下拉、沒有「登記」按鈕 | 自動：`T` |
| D08 | 作法 3（no_module_system）；原話 2 | 功能 | ann-ce 清單 `no_module_system` | 開 `/settings` | 顯示計畫給的完整句：「此站台沒有找到已安裝的 nf-core 模組：送出時直接取用 nf-core 官方版本。若管線裝在模組以外的位置，請使用下方「進階：手動填寫」。」；沒有下拉 | 自動：`T` |
| D09 | 作法 3（清單空）；原話 2 | 功能 | ann-ce 清單 `ok` 但 `items` 為空 | 開 `/settings` | 顯示與 D08 相同的那一句；沒有下拉 | 自動：`T` |
| D10 | 作法 3（error）；專長守則（失敗狀態） | 例外 | ann-ce 清單 `error`，原因文字含 `<script>x</script>` | 開 `/settings` | 顯示「✕ 未能讀取站台清單：<原因>」（符號與文字俱在），原因文字被轉義（頁面不含未轉義的 `<script>`）；有按鈕「重新讀取站台清單」；沒有下拉；原因不含內部路徑、堆疊 | 自動：`T` |
| D11 | 作法 3（已登記的不列；邊界） | 功能 | ann-ce 清單 `ok`，兩個項目都已登記 | 開 `/settings` | 頁面正常（200）；下拉不含任何已登記項（沒有可選項目時不得出現可送出的選項）；仍有「重新讀取站台清單」按鈕與「進階：手動填寫」；沒有錯誤。（畫面該寫什麼句子計畫未訂，見總覽疑問 2） | 自動：`T` |
| D12 | 作法 3（進階區）；原話 3 | 功能 | slurm 環境分別處於 ok 有項目、none、no_module_system、error 四種狀態 | 開 `/settings` | 四種狀態底部都有收合的 `<details>`（沒有 `open` 屬性），標題逐字「進階：手動填寫（管理者用）」（英文為訂定句）；內容是 #259 的四格表單：標籤逐字為「管線（例 nf-core/ampliseq）」「版本（例 2.18.0）」「模組名稱（站台 module load 使用的名稱，例 biology/nf-core-ampliseq/2.18.0）」「管線資料夾變數（模組設定的環境變數名稱，例 NFCORE_AMPLISEQ_HOME）」，四欄皆 `required`，送往 `/settings/pipelines`、`op=add`；已登記清單旁的「移除」小表單照舊 | 自動：`T` |
| D13 | 原話 5；作法 4（英文版面） | 功能 | `?lang=en`，slurm 四種狀態與雲端環境 | 開設定頁、走 `pick` 第一步與第二步 | 全程為英文，沒有跳回中文；各狀態句、標籤、按鈕、進階區標題、進階區四格標籤（Pipeline (e.g. nf-core/ampliseq) 等 #259 的英文標籤）都是「出題者訂定的字串」表所列英文；確認頁按鈕為 Confirm、Back | 自動：`T` |
| D14 | 原話 5；作法 4 | 功能 | 本任務新增的每個字串鍵 | 檢查字串表（`web_board.py` 的 STRINGS） | 每個新鍵都有非空的中文與英文；英文字串不含中文字；英文頁面所有新增文字都是英文 | 自動：`T` |
| D15 | 作法 4；DESIGN「用字」；DESIGN 2026-10-27 原話（中文不能口語） | 功能 | 本任務新增的全部中文字串（含訂定的通知句、400 句、雲端一句） | 以 DESIGN.md「用字」禁用字清單比對（用過、選好、寫死、自己填、自己調整、你還沒、還沒有、還不能、這個、這份、這條、這一版、一下、弄、搞、東西、喔、啦、吧、囉、蠻、超） | 沒有任何一個禁用字出現。（計畫的 400 句含「這個版本」，與清單中的「這個」衝突，見總覽疑問 1；該句為計畫逐字指定，TC 以計畫句為準，不算違規，但其餘新字串不得含禁用字） | 自動：`T` |
| D16 | DESIGN 原話 13；作法 3 | 功能 | 設定頁各狀態、確認頁 | 讀按鈕文字 | 按鈕只用固定動詞：登記、移除、確認、返回，與計畫指定的「重新讀取站台清單」；英文為 Register、Remove、Confirm、Back、Reload site list；按鈕上沒有數字、版本或檔名 | 自動：`T` |
| D17 | 作法 3（只用現有 class；前端限制） | 功能 | 渲染設定頁各狀態（含通知與錯誤）、確認頁 | 檢查 HTML | 沒有 `style=` 屬性；沒有 `<script`；沒有指向外部網址（`http://`、`https://`）的資源；沒有外部字型或圖片 | 自動：`T` |
| D18 | 計畫「不改安全標頭」 | 功能 | 對 `GET /settings`、`pick` 的 `POST /settings/pipelines`（成功與失敗）、重新讀取路由（成功與失敗）取得回應 | 讀回應標頭 | 每個回應的 Content-Security-Policy 與 `web._HEADERS` 完全相同，並帶 `Cache-Control: no-store`、`X-Frame-Options: DENY` | 自動：`T` |
| D19 | 作法 3（不改 STYLE）；原話 4 | 功能 | 比對 base | 檢查新標記用到的 class 與樣式表 | 新標記用到的每個 class 都已存在於現有樣式表；樣式表與 base 相同（D13 釘住的 sha256 不變）；沒有新增顏色、字型、間距數值 | 自動：`T` 與既有 STYLE sha256 測試 |
| D20 | 專長守則（狀態不只靠顏色）；DESIGN 原話 7 | 功能 | 渲染：error 狀態、`inv_queued`／`inv_no_agent` 通知、400 錯誤句、none／no_module_system 狀態句 | 檢查 HTML | 錯誤與通知句同時含符號（✓／○／✕）與文字；none、no_module_system 與雲端的狀態以文字句呈現（計畫句本身無符號），不是只靠 class 或顏色區分 | 自動：`T` |
| D21 | backend 守則（跨使用者讀） | 例外 | ann、ben 各有環境與不同的清單 | ben 開 `/settings`；ann 開 `/settings` | 各自只看到自己的環境與清單項目；ann 的清單項目與環境名稱不出現在 ben 的頁面，反之亦然 | 自動：`T` |
| D22 | DESIGN 空狀態 | 例外 | ann 沒有任何運算環境 | 開 `/settings` | 仍顯示既有的「沒有運算環境。」，沒有登記或重新讀取表單，頁面 200 | 自動：`T` |
| D23 | 作法 3（每個環境區塊依類型） | 功能 | ann 同時有 slurm 環境與雲端環境 | 開 `/settings` | 各區塊依自己的類型顯示對應畫面（slurm 的下拉區、雲端的一句），互不影響；每區塊有 `id="ce-<名稱>"` 錨點；slurm 環境的通知出現在自己那一列上方 | 自動：`T` |
| D24 | 失敗先行測試（GET 不改資料庫） | 功能 | 記下資料庫；環境涵蓋 slurm 四種狀態與雲端 | 對 `/settings` 發出帶各種 notice 值的 GET | 資料庫完全不變（GET 不寫入、不排預檢） | 自動：`T` |

## 6. 維護者原話的端到端（原話 1、2、3）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| E01 | 原話 1「我不太清楚登記管線哪邊o不ok，不知道怎麼填」 | 功能 | ann-ce 清單 `ok`（ampliseq 2.18.0）；使用者只知道要用 `nf-core/ampliseq 2.18.0` | 只做兩件事：在下拉選 `nf-core/ampliseq 2.18.0` 按「登記」，再在確認頁按「確認」（不輸入任何模組名稱或變數） | 登記完成：`sitePipelines` 含該筆，module 與 home 由平台帶入；使用者全程沒有輸入過模組名稱或變數名稱 | 自動：`T` |
| E02 | 原話 2（叢集沒有模組系統／沒裝任何 nf-core 模組，照常可送出，取用官方版本） | 功能 | ann-ce 清單 `no_module_system`（另測 `ok` 但 `items` 空），`sitePipelines` 為空 | 開 `/launch` 選 ann-ce 與任一 nf-core 版本，送出 | 第 3 步不顯示「尚未登記」提示；送出不被 `e_reg` 拒絕（與 #259 的空清單語意相同） | 自動：`T` |
| E03 | 原話 2（雲端每次直接取用官方版本，不需登記） | 功能 | 雲端環境 ann-gcb，沒有 `sitePipelines` | 開 `/launch` 選 ann-gcb 與任一 nf-core 版本 | 不顯示「尚未登記」提示；不被 `e_reg` 拒絕；設定頁上該環境沒有任何登記步驟 | 自動：`T` |
| E04 | 原話 3「登記管線要做，畢竟是裝在使用者自己租的伺服器或國網」 | 功能 | ann-ce（slurm）清單 `no_module_system` | 經「進階：手動填寫」登記一筆（四格），走完兩步確認 | 登記成功寫入；證明管線裝在模組以外位置時仍可登記 | 自動：`T` |

## 7. 文件與手動項目

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| M01 | 完成標準（1440／390 × zh／en 四種狀態無橫向捲動）；專長守則（手機可用） | 功能 | 瀏覽器視窗 1440 與 390 px 寬，中文與 `?lang=en`；slurm 的 ok 有項目、none、no_module_system／清單空、error 四種畫面 | 開設定頁上下左右捲動 | 沒有橫向捲軸；下拉、按鈕可點、不被切掉 | 手動：`docs/TESTING.md` 新增節 |
| M02 | 專長守則（鍵盤、焦點外框） | 功能 | 開設定頁 | 只用 Tab 鍵走過下拉、「重新讀取站台清單」、「登記」、進階區標題（可展開）、進階表單欄位、確認頁按鈕 | 每個可操作項目取得焦點時有看得見的外框；進階區可用鍵盤展開 | 手動：`docs/TESTING.md` 新增節 |
| M03 | 計畫「範圍：檔案」docs/TESTING.md；原話 1 | 功能 | nano4 真站台（維護者的國網帳號），站台上已用 `module` 裝好 `nf-core/ampliseq 2.18.0` | 在設定頁按「重新讀取站台清單」，等代理回報後重新整理；下拉選 `nf-core/ampliseq 2.18.0` 登記；看確認頁 | 下拉出現 `nf-core/ampliseq 2.18.0`；確認頁顯示 `biology/nf-core-ampliseq/2.18.0` 與 `NFCORE_AMPLISEQ_HOME`；按確認後登記出現在清單 | 手動：`docs/TESTING.md` 新增節（維護者執行） |
| M04 | 計畫「範圍：檔案」docs/SETTINGS.md | 功能 | 讀文件 | 檢查 `docs/SETTINGS.md` 約 :329「Register from the web page」段 | 已改寫為：叢集環境從站台已安裝清單挑選、雲端不顯示登記、手動四格收在「進階」；與實際行為一致 | 手動：閱卷者讀文件 |
| M05 | 計畫「範圍：檔案」docs/TESTING.md | 功能 | 讀文件 | 檢查 `docs/TESTING.md` 新增的手動一節 | 逐條含：M01（四種畫面×兩種寬度×兩種語言）、M02、M03 的步驟；每條具體到可照做 | 手動：閱卷者讀文件 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| X01 | 不做：不新增 job kind、不做 migration | 不在範圍 | 比對 base | 比較資料庫結構（所有表與欄位、`jobs.kind` 的 CHECK 限制）；用 base 版建出的舊資料庫走完 `pick` 登記與重新讀取 | 結構與 base 相同，沒有新表、新欄位、新 migration 檔；舊資料庫可完整運作；盤點只掛在 preflight 內 | 自動：`T` |
| X02 | 不做：不做 MCP 工具；parity 列為網頁專用唯讀輔助 | 不在範圍 | 列出 MCP 伺服器工具清單 | 與 base 比對 | 工具清單與 base 完全相同；沒有 `site_pipeline_inventory`、重新讀取或 `pick` 相關工具 | 自動：`T` |
| X03 | 不做：不改 `sitePipelines` 驗證規則 | 不在範圍 | 比對 base | 比較 `compute_envs.py`（`_module_problem`、`_var_problem`、`_check_site_keys` 的 sitePipelines 部分）與 `abf_station/rules.py` 的驗證 | 規則與 base 相同；既有 `clean()` 驗證測試無任何修改且全綠 | 自動：既有 compute_envs 測試；閱卷者以 `git diff` 比對 |
| X04 | 不做：不幫使用者裝模組 | 不在範圍 | 攔截盤點指令與所有 ssh 呼叫 | 走完盤點、挑選、登記 | 不出現 `module load`、安裝、`pip`、`conda` 或任何改動站台的指令；沒有「安裝」按鈕或路由 | 自動：`S` 與 `T` |
| X05 | 不做：不自動偵測模組以外的位置（留進階手填） | 不在範圍 | 假站台 `module` 不存在但某路徑有管線資料夾 | 執行 preflight、開設定頁 | 盤點只送 `module` 相關指令，不探查其他路徑；畫面只給 D08 的句子與進階手填入口，沒有自動帶入任何項目 | 自動：`S` 與 `T` |
| X06 | 不做：不改安全標頭與 STYLE | 不在範圍 | 比對 base | 比較 `web._HEADERS` 與樣式表 sha256 | 與 base 相同；D13 釘死測試無任何修改 | 自動：既有 STYLE／標頭測試與 D18、D19 |
| X07 | 範圍「平台不開對外連線」 | 不在範圍 | 把對外連線（socket）封鎖 | 走完開設定頁、挑選兩步、重新讀取 | 平台沒有任何對外連線嘗試；站台資訊只經站台代理的工作傳遞 | 自動：`T` |
| X08 | 範圍：既有被釘住的測試「只加不刪」，ledger 逐條列 | 不在範圍 | 比對 base 與 `ledger.md` | 檢查被改動的既有測試檔（預期 `test_web_settings_register.py` 表單結構從四格變下拉＋進階的斷言、`test_web_parity.py`、`test_actions_layer.py` 如有） | 只有新增項或計畫明寫要跟著改的斷言；沒有刪除、跳過或放寬；ledger 逐條列出每處被改的斷言與理由；本任務未修改 spec／test-case*.md | 手動：閱卷者以 `git diff` 比對 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| K01 | Safety Net（不經確認不得寫入）；原則 1 第 2 點（人的管道） | 例外 | 掃描 `web.py` 與 `web_settings.py` 全部路由 | 以語法樹找出呼叫 `register_site_pipeline`／`remove_site_pipeline` 的位置，並確認 #259 的「缺管道一律拒絕」測試仍在且全綠 | 只有第二步 `/settings/pipelines/confirm` 的處理函式呼叫它們，且帶 `actions.PAGE`；`pick` 的第一步與所有 GET 只讀（只呼叫 `site_pipeline_inventory`、`check_site_pipeline_change`）；`register_site_pipeline` 對缺／假 `confirmed_by` 仍拒絕且資料庫不變 | 自動：`T` 與既有 `test_actions_layer.py` |
| K02 | backend 守則（對等性）；`test_web_parity.py` | 功能 | 動作層公開名稱 | 執行 parity 測試 | `site_pipeline_inventory` 列為網頁專用唯讀輔助（WEB_ONLY 或 INTERNAL，附理由）；重新讀取若新增公開動作也各在一張表；四張表聯集等於公開名稱、彼此不重疊 | 自動：`platform/tests/test_web_parity.py` |
| K03 | backend 守則（路由裡不得有第二份邏輯） | 功能 | 檢視 `web.py` 的 `pick` 與重新讀取路由 | 檢查匯入與資料來源 | `web.py`、`web_settings.py` 不匯入 `confirm`、`jobs`、`compute_envs`、`agents`、`status`（parity 測試的 FORBIDDEN_IMPORTS）；`pick` 的清單只從 `actions.site_pipeline_inventory`（帶登入者）取得，不直接讀資料庫；寫入與排預檢都在動作層 | 自動：`test_web_parity.py` 與 `T` |
| K04 | Safety Net（憑證不外洩）；backend 守則（日誌與回應不含密鑰） | 例外 | 走完 `pick`、重新讀取與各種失敗（B03–B10、R03–R06、D10），擷取回應與日誌 | 在其中搜尋 | 回應與日誌不含：登入階段 cookie 值、密碼、任何權杖、堆疊（`Traceback`、`File "`）、`SELECT`／`sqlite`、伺服器內部路徑；CSRF 值只出現在表單 hidden 欄位；盤點指令與結果不含環境憑證 | 自動：`T` |
| K05 | backend 守則（錯誤訊息說明發生什麼與怎麼處理） | 例外 | B04–B06、B14、R03、D10 的失敗回應 | 讀訊息 | `pick` 找不到的訊息含下一步（按「重新讀取站台清單」）；403 頁說明什麼都沒有改並請重新整理；讀取失敗句說明原因；無一是空白頁或只有狀態碼 | 自動：`T` |
| K06 | 憲法 3（不得有寫死路徑）、1（每個程式標明替代品） | 功能 | 新增與修改的 Python／文件檔 | 執行 `bash tests/no_hardcoded_paths.sh`、`bash tests/scripts_name_their_alternative.sh` | 兩者通過（`biology/...` 只作為範例名稱；新測試檔與新增程式檔頭有 `# Nothing existing:` 或 `# Not <tool>:` 說明） | 自動：`tests/no_hardcoded_paths.sh`、`tests/scripts_name_their_alternative.sh` |
