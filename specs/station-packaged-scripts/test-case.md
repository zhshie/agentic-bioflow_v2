# 測試案例：pip 安裝的站台代理自帶 scripts/ 與 configs/，不必再給 --plugin-root

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Every row can be judged without reading code.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/station-packaged-scripts/plan.md`（本任務沒有 spec.md；計畫含「目標／作法／裁決一～三」，維護者原話：無，驗收情境見計畫「維護者原話」一節）　**總覽**：`test-case-overview.md`

名詞先說明：

- **wheel**：`pip install` 用的安裝包，裡面是解開後會放進 Python 環境的檔案。
- **plugin root（外掛根目錄）**：一個資料夾，底下有 `scripts/on_site.sh`（連到站台的腳本）和 `configs/`。`abf-station run` 靠它找到腳本。
- **packaged 複本**：建置 wheel 時，從 repo 的 `scripts/` 與 `configs/` 複製進 `abf_station/plugin/scripts/` 與 `abf_station/plugin/configs/` 的那一份。
- **checkout**：直接從 git repo 資料夾跑（舊行為），此時 repo 根目錄就是 plugin root。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

比對檔案內容時，一律排除 `__pycache__` 與 `*.pyc`（裁決三第 11 條）。測試檔都放在 `platform/tests/test_station_packaging.py`，除非另寫。

## User Story 1 — 只裝 wheel 的環境，`abf-station run` 不給 `--plugin-root` 也找得到腳本（優先度 P1）

維護者原話：無。這是 2026-10-23 桌機部署實際踩到的 bug，驗收情境＝「在一個只裝了 wheel、沒有 repo 的環境，`abf-station run` 的部署檢查不再因找不到 on_site.sh 而拒跑」，見 TC-SP-07。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-SP-01 | 作法 1；計畫測試 `test_sp01` | 功能 | 一份 repo 副本（含 `skills/`、`scripts/`、`configs/`、`platform/`） | 用 `pip wheel --no-deps` 建 wheel（做法同 TC-404） | wheel 內有 `abf_station/plugin/scripts/on_site.sh`、`settings.sh`、`egress_allow.sh` 三個檔，內容與 repo 的 `scripts/` 同名檔逐位元相同 | 自動：`test_sp01_wheel_ships_the_scripts_folder` |
| TC-SP-02 | 作法 1、裁決二第 5 條 | 功能 | 同 TC-SP-01 的 wheel | 列出 wheel 內 `abf_station/plugin/scripts/` 底下所有檔案，與 repo `scripts/` 底下所有檔案比對 | 兩邊檔案清單（含 `dev/`、`intro/`、`utils/` 等子資料夾裡的檔）完全一致，每個檔逐位元相同；不多也不少 | 自動 |
| TC-SP-03 | 裁決二第 4 條 | 功能 | 同 TC-SP-01 的 wheel | 列出 wheel 內 `abf_station/plugin/configs/sites/` 底下所有檔案，與 repo `configs/sites/` 比對 | 檔案清單一致（含 `su_rates.json`、`nchc.config` 等），每個檔逐位元相同 | 自動 |
| TC-SP-04 | 作法 2；計畫測試 `test_sp02` | 功能 | 暫存目錄裡假造 `abf_station/plugin/scripts/on_site.sh`，並讓模組路徑指到那裡（monkeypatch） | 呼叫 `site.default_plugin_root()` | 回傳 `<假 abf_station>/plugin`（packaged 路徑），不是 repo 根 | 自動：`test_sp02_default_plugin_root_prefers_the_packaged_copy` |
| TC-SP-05 | 作法 2；計畫測試 `test_sp03` | 功能 | 直接從 checkout 跑，`abf_station/plugin/` 不存在 | 呼叫 `site.default_plugin_root()`，再用回傳值呼叫 `site.on_site_script(...)` | 回傳 repo 根（`Path(__file__).resolve().parents[2]`，舊行為），且 `on_site_script(...)` 指到的檔案存在 | 自動：`test_sp03_checkout_falls_back_to_repo_root` |
| TC-SP-06 | 作法 2「`--plugin-root` 仍優先」；計畫測試 `test_sp04` | 功能 | 同時存在 packaged 複本，和一個使用者另外指定的資料夾 X（內有 `scripts/on_site.sh`） | 用 `--plugin-root X` 跑部署檢查／啟動流程（`run` 與 `unforward` 各確認一次） | 實際用到的是 X 下的腳本，不是 packaged 複本；X 缺腳本時，訊息點名的是 X 下的路徑 | 自動：`test_sp04_explicit_plugin_root_still_wins` |
| TC-SP-07 | 計畫「驗收情境」 | 功能 | 把 TC-SP-01 的 wheel 解開到一個空資料夾（完全沒有 repo、不在 repo 路徑下），另有一個部署資料夾，內含 `config/env.yaml` | 在那個環境（只認解開的 wheel）匯入 `abf_station`，取 `default_plugin_root()`，再呼叫 `cli.deployment_problem(部署資料夾, default_plugin_root())` | `default_plugin_root()` 落在解開的 wheel 內（`.../abf_station/plugin`）；`deployment_problem` 回傳 `None`（不再因找不到 on_site.sh 而拒跑） | 自動 |
| TC-SP-08 | 作法 3 | 功能 | 取 TC-SP-01 wheel 內的 plugin 資料夾複本（不假設檔案帶執行位元） | 用 `Site(plugin_root, 設定檔).call(...)` 呼叫一次站台腳本，搭配既有測試用的乾跑縫（`ON_SITE_DRY_RUN`，不連線） | 腳本確實被啟動：結果不是「cannot start the site script」（rc 127），也不是找不到檔案；Site 仍是以 `bash <路徑>` 的方式呼叫，即使沒有執行位元也能跑 | 自動 |
| TC-SP-09 | 裁決二第 4 條（reach=ssh） | 功能 | 取 packaged plugin 資料夾當 root | 對該 root 實跑 `tar -cz -C <root> scripts configs` 輸出到 `/dev/null` | tar 成功（exit 0）；另列出內容，含 `scripts/on_site.sh` 與 `configs/sites/su_rates.json`，代表 ssh 模式送出去的包是完整的 | 自動 |
| TC-SP-10 | 作法 2、cli 第 114 行 | 功能 | 同 TC-SP-07 的環境 | 不給 `--plugin-root`，走 `unforward` 的預設 plugin root 流程到部署檢查 | 部署檢查通過（回傳 `None`），`unforward` 與 `run` 用同一個預設，不再各寫一份舊的 `parents[2]` | 自動 |

## User Story 2 — 找不到腳本或來源時，講清楚發生什麼、怎麼處理（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-SP-11 | 裁決二第 6 條、裁決三第 9 條 | 例外 | 安裝裡沒有 packaged 複本，repo 根也沒有 `scripts/on_site.sh`（暫存目錄模擬），使用者沒給 `--plugin-root`；部署資料夾正常 | `abf-station run`（走 `cmd_run`） | 拒絕啟動（回傳拒絕碼，不是堆疊錯誤）；訊息含腳本的完整路徑，並說明「安裝版裡沒有」「也沒給 `--plugin-root`」「請用 `--plugin-root` 指定」這幾層意思；不鎖語言與逐字措辭，但至少要有腳本路徑與字串 `--plugin-root`，且與舊訊息不同（有補上安裝版沒有的說明） | 自動 |
| TC-SP-12 | 同上，cli 第 114 行 | 例外 | 同 TC-SP-11 | `abf-station unforward`（走 `cmd_unforward`） | 同樣拒絕，訊息同樣含腳本路徑與 `--plugin-root` 的處理方式 | 自動 |
| TC-SP-13 | 專長守則：錯誤訊息與日誌 | 例外 | 同 TC-SP-11；token 檔裡放一個辨識用字串 | 觸發拒絕，收集畫面輸出與日誌 | 輸出沒有 Traceback/堆疊、沒有 SQL；token 檔內容的字串不在任何輸出裡；訊息所含路徑只限使用者需要知道的腳本位置（裁決三第 9 條的例外） | 自動 |
| TC-SP-14 | 裁決三第 8 條 | 例外 | 一份暫存 repo 副本，有 `skills/`、`configs/`，**沒有** `scripts/` | 對它跑 `pip wheel` | 建置失敗（非 0），沒有產出 wheel；輸出指出找不到 `scripts`，不會做出缺腳本的 wheel | 自動 |
| TC-SP-15 | 裁決三第 8 條 | 例外 | 一份暫存 repo 副本，有 `skills/`、`scripts/`，**沒有** `configs/` | 對它跑 `pip wheel` | 建置失敗（非 0），沒有產出 wheel；輸出指出找不到 `configs` | 自動 |

## User Story 3 — 建置產物不進 git，既有的打包測試不被弄壞（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-SP-16 | 裁決二第 7 條；計畫測試 `test_sp05`（仿 TC-408） | 功能 | 這個 repo | 讀 `.gitignore`，並問 git 追蹤了哪些 `platform/abf_station/plugin` 底下的檔 | `.gitignore` 有 `platform/abf_station/plugin/` 這一行（整行相符）；`git ls-files platform/abf_station/plugin` 為空 | 自動：`test_sp05_copy_is_gitignored_and_untracked` |
| TC-SP-17 | 裁決三第 8 條後段 | 功能 | `test_guidance.py` 的 `_copy_for_build` 改成暫存 repo 也帶 `scripts/` 與 `configs/` | 跑 TC-404 | 通過，且 TC-404 的斷言文字與 base 相同（仍比對 `skills` 六個檔、`sorted(got)==sorted(want) and len(want)==6`、`got==want`），沒有放寬 | 自動：`test_guidance.py::test_tc404_*` |
| TC-SP-18 | 裁決二第 2 條、裁決三第 10 條 | 功能 | 實作完成後的 `pyproject.toml` 與 `test_guidance.py` | 跑 TC-406、TC-407 | 兩者通過。TC-406 若有改，只能是「仍要求 `abf_platform` 含 `skills/*/SKILL.md` 那一條」並另外允許 `abf_station` 的 plugin scripts／configs；`packages` 清單不變（TC-407），`abf_station/plugin` 不被當成新的 Python 套件；ledger 有寫「以前／以後」 | 自動：`test_guidance.py::test_tc406_*`、`test_tc407_*`；ledger 內容由閱卷核對 |
| TC-SP-19 | 完成標準「全套綠」、裁決一 | 功能 | 實作完成，在 WSL／Linux 跑 `tests/run_all.sh` | 跑全套 | 全套綠。唯一可接受的紅是 `tests/init_workspace_test.sh` 的「site side with no run area known」一條，且該條在 base 同樣紅；有這種情況時報告要註明 | 自動：`tests/run_all.sh` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-SP-20 | 「不做」第 1 條：不改 on_site.sh | 不在範圍 | 實作完成 | 比對 `scripts/on_site.sh` 與 base（`v3`）的差異 | 沒有任何差異；packaged 複本只是 TC-SP-01 所述的逐位元拷貝 | 自動：以 git 對 base 比對（閱卷時再用 `git diff v3...HEAD` 複核） |
| TC-SP-21 | 「不做」第 1 條：不改 su.py | 不在範圍 | 實作完成 | 比對 `platform/abf_platform/su.py` 與 base 的差異 | 沒有任何差異（它讀 `configs/sites/su_rates.json` 的方式維持原樣，本件不改成 packaged 版） | 自動：同 TC-SP-20 |
| TC-SP-22 | 環境事實：su.py 潛在問題記進 ledger 的「欠」 | 不在範圍 | 實作完成 | 讀 `specs/station-packaged-scripts/ledger.md` | 有一條「欠」，點名 `su.py`（讀 `configs/sites/su_rates.json`）有同類潛在問題、本件未處理 | 自動：文字檢查 ledger；內容由閱卷核對 |
| TC-SP-23 | 「不做」第 1 條：不改站台協定；裁決 3 不需要 migration | 不在範圍 | 實作完成 | 列出與 base 相比有變動的檔案 | 全部落在計畫「範圍：檔案」（含 `test_guidance.py`、`specs/station-packaged-scripts/` 與只限建置產物的 `platform/abf_station/plugin/` 不提交）之內；沒有資料庫 schema、migration 檔（如 `*.sql`、migration 資料夾）的變動；站台協定相關檔（`agent.py`、`handlers.py`、`protocol` 類）沒有變動 | 自動：同 TC-SP-20 |
| TC-SP-24 | 「不做」：不改站台協定、不增加新的啟動方式 | 不在範圍 | 實作完成 | 讀 `cli.py` 的 `build_parser()` 與 `--plugin-root` 的用法 | 兩個子指令（`run`、`unforward`）的參數列不增不減，`--plugin-root` 仍存在且仍優先於預設 | 自動 |

## 憲法與安全網

本任務動到：原則 I.1（新增檔案要寫明「不是什麼工具」的標頭）、原則 II.3（不寫死個人或叢集路徑）、原則 V.11（腳本從 `${BASH_SOURCE[0]}` 找自己，且拒絕訊息要說清楚是缺哪一種東西）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-SP-25 | I.1：每個新檔寫明為什麼是自己寫的 | 功能 | 新增的 `platform/tests/test_station_packaging.py`、改過的 `setup.py`、`site.py`、`cli.py` | 看每個檔的第一行 | 新檔第一行是 `# Nothing existing: …` 或 `# Not <工具>: …` 形式的標頭（與 `test_station_static.py` 等既有測試檔一致）；`setup.py` 既有標頭仍在 | 自動：`tests/scripts_name_their_alternative.sh`（若涵蓋）；否則由 `test_tc410` 同類檢查與閱卷核對 |
| TC-SP-26 | II.3：不寫死路徑 | 功能 | 實作完成 | 跑 `bash tests/no_hardcoded_paths.sh` | 通過；新程式與新測試沒有個人路徑（如 `/mnt/c/...`、家目錄）、叢集路徑 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-SP-27 | V.11：腳本從自己的位置找鄰居，不靠目前資料夾；拒絕要說是缺哪一種東西 | 功能 | packaged plugin 資料夾複本；目前工作資料夾刻意設成別處（例如一個空的暫存目錄） | 從那個別處的資料夾，以絕對路徑啟動 packaged 的 `on_site.sh`（乾跑縫，不連線） | 腳本照常找到同資料夾的 `settings.sh`（不因工作資料夾不同而失敗）；而 TC-SP-11 的拒絕訊息說的是「外掛資料夾（plugin folder）」缺腳本，明確是資料夾層級的問題，不是 shell 或其他能力的問題 | 自動：`tests/on_site_test.sh` 與 `test_station_packaging.py` |

<!--
專長守則（backend）對照：
- 錯誤訊息與日誌 TC：TC-SP-11、12、13。
- 資料結構／migration：TC-SP-23（計畫裁決 3 明寫「不需要 migration」，且無 schema 變動）。
- 對等性、跨使用者、確認管道三類：本任務沒有新增或修改任何網頁／API／聊天動作，也沒有任何寫入使用者紀錄的動作（建置只寫暫存的 build_lib），所以沒有對應 TC；閱卷時由 verifier 確認變動檔案清單中沒有路由、動作層或寫入路徑（TC-SP-23）。
-->
