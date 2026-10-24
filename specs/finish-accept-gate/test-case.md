# 測試案例：打包交付前擋下未驗收的分析條目（issue #12）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/finish-accept-gate/plan.md`（本任務沒有獨立的 spec.md，計畫即規格；維護者的話＝計畫裡逐字引用的 issue #12 本文與「裁決二」）　**總覽**：`test-case-overview.md`

**名詞（一句話）**：「條目」＝ `analysis/analysis.md` 裡的一個分析項目（有 id、question、status）。「接受」＝該條目的 `status` 去掉頭尾空白、轉小寫後**恰好**是 `accepted` 或 `done`。「建包」＝執行 `scripts/build_package.sh`，產出 `submission/`（`manuscript.qmd`、`report.md`、`provenance.json` 等）。「退 2」＝程式結束代碼 2，代表『被擋下』。

測試編號沿用計畫的 `TC-G01`～`TC-G15`，計畫一條對多個預期的就拆成 a、b、c；`TC-G16` 起是出題者補的（來自 issue 本文的情境與計畫的決定）。實作測試時，每條都要在註解裡寫出自己的編號。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

所有「自動」案例的夾具：在 `$TMP/gate_*` 下各自建一個最小專案（`runs/demo_20260101/results/pipeline_info/` 加 `analysis/analysis.md`），不連網（`CITE_CURL=false`、`ABF_PIPELINE_FETCHER=off`）。

## User Story 1 — 只要有一條沒被接受，就拒絕建包（優先度 P1）

issue #12 第 2 點：使用者問了幾個追問就直接打 `/finish`，從沒說過「接受」，代理卻照建了包。要的是機械式的擋，不是靠代理自覺。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-G01a | issue #12 第 2 點；決定一、四、七；手算範例 1 | 例外 | analysis.md 區塊格式，只有一條：`- **richness**`／`  id: richness`／`  question: Q?`／`  status: proposed` | 對這個專案執行 `build_package.sh` | 結束代碼是 2（不是 0） | 自動：`tests/build_package_test.sh` |
| TC-G01b | 決定七（固定子字串） | 例外 | 同 TC-G01a | 同上，看錯誤輸出（stderr） | 同時含 `refusing to build`、`not accepted`、`richness`、`status: proposed` | 自動：`tests/build_package_test.sh` |
| TC-G01c | 決定七；手算範例 1 | 例外 | 同 TC-G01a | 同上，看錯誤輸出的前兩行 | 第一行是 `build_package.sh: refusing to build - 1 of 1 entries in <analysis.md 的實際路徑> are not accepted:`；第二行是 `  richness   status: proposed`（兩個空格開頭、id 後三個空格） | 自動：`tests/build_package_test.sh` |
| TC-G01d | 決定七；裁決二第 3 點 | 例外 | 同 TC-G01a | 同上，看錯誤輸出 | 含 `Moving on to`（「換去 /finish 或追問不算接受」那句）與 `status: accepted`（告訴使用者要在該條目加上什麼） | 自動：`tests/build_package_test.sh` |
| TC-G01e | 目標第 3 點；決定七「Nothing was written」必須是真的 | 例外 | 同 TC-G01a，事前 `submission/` 不存在 | 執行 `build_package.sh` | 錯誤輸出含 `Nothing was written to`；而且 `submission/` 目錄**真的不存在**（沒有半成品資料夾） | 自動：`tests/build_package_test.sh` |
| TC-G16 | issue #12 第 2 點的現場：四條分析、使用者只追問、從沒說接受 | 例外 | analysis.md 有四條（id 各異，例如 `richness`、`evenness`、`beta`、`pcoa`），四條都是 `status: proposed` | 執行 `build_package.sh` | 結束代碼 2；錯誤輸出第一行含 `4 of 4 entries`；四個 id 都被列出，每條帶 `status: proposed`；`submission/` 不存在 | 自動：`tests/build_package_test.sh` |
| TC-G02a | 決定七；手算範例 2 | 例外 | 兩條：`richness` 是 `accepted`、`evenness` 是 `revised`（區塊格式） | 執行 `build_package.sh` | 結束代碼 2；第一行含 `1 of 2 entries`；列出 `evenness` 與 `status: revised` | 自動：`tests/build_package_test.sh` |
| TC-G02b | 決定七（只列未接受的） | 例外 | 同 TC-G02a | 同上，看錯誤輸出 | 輸出中**完全沒有** `richness`（已接受的不列） | 自動：`tests/build_package_test.sh` |
| TC-G02c | 目標第 3 點 | 例外 | 同 TC-G02a | 同上 | `submission/` 不存在（一條沒接受，整包都不建） | 自動：`tests/build_package_test.sh` |
| TC-G03 | 決定三、四；TC-G03 | 例外 | 區塊格式，一條 `id: richness`、`question: Q?`，**完全沒有** `status:` 那一行 | 執行 `build_package.sh` | 結束代碼 2；錯誤輸出含 `status: (none)` | 自動：`tests/build_package_test.sh` |
| TC-G04 | 決定三；裁決二第 3 點（舊條目沒有 status 欄也擋）；手算範例 4 | 例外 | 表格格式，表頭只有 `\| id \| question \|`，一列 `\| fig1 \| Q? \|`（沒有 status 欄） | 執行 `build_package.sh` | 結束代碼 2；錯誤輸出含 `fig1` 與 `status: (none)` | 自動：`tests/build_package_test.sh` |
| TC-G05 | 決定四（拼法不在清單，不做同義詞） | 例外 | 一條 `status: approved` | 執行 `build_package.sh` | 結束代碼 2；錯誤輸出含 `status: approved` | 自動：`tests/build_package_test.sh` |
| TC-G08 | 決定四（不做前綴比對） | 例外 | 一條 `status: accepted-ish` | 執行 `build_package.sh` | 結束代碼 2 | 自動：`tests/build_package_test.sh` |
| TC-G17 | 決定四（`not accepted` 不算） | 例外 | 一條 `status: not accepted` | 執行 `build_package.sh` | 結束代碼 2；錯誤輸出含 `status: not accepted`；`submission/` 不存在 | 自動：`tests/build_package_test.sh` |
| TC-G18 | 決定四（空字串不算） | 例外 | 區塊格式，一條 `status:` 後面什麼都沒寫 | 執行 `build_package.sh` | 結束代碼 2；錯誤輸出含該條 id 與 `not accepted`；`submission/` 不存在 | 自動：`tests/build_package_test.sh` |
| TC-G11 | 決定六（#38 項目 2：沒有 id 的列也檢查） | 例外 | 表格格式（含 status 欄）有兩列：一列 id 空白、question 有字、`status: proposed`；另一列 `fig1`、`accepted` | 執行 `build_package.sh` | 結束代碼 2；錯誤輸出含 `(no id)` | 自動：`tests/build_package_test.sh` |

## User Story 2 — 全部接受時，照常建包，不多不少（優先度 P1）

計畫的目標是「只讓安全網更嚴」：已接受的條目建出來的東西，要和改動前一模一樣。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-G06a | 決定四；手算範例 3 | 功能 | 兩條：`richness` 是 `accepted`、`evenness` 是 `done` | 執行 `build_package.sh` | 結束代碼 0；標準輸出有 `wrote     submission/manuscript.qmd`；`submission/manuscript.qmd` 存在 | 自動：`tests/build_package_test.sh` |
| TC-G06b | 決定四 | 功能 | 同 TC-G06a | 打開建出來的 `manuscript.qmd` | 兩條的 question 文字都在裡面 | 自動：`tests/build_package_test.sh` |
| TC-G07 | 決定四（去空白、轉小寫） | 功能 | 一條 `status: Accepted `（大寫 A，後面多一個空格） | 執行 `build_package.sh` | 結束代碼 0，建出 `submission/manuscript.qmd` | 自動：`tests/build_package_test.sh` |
| TC-G19 | 「必須更新的既有斷言」：沒有任何既有測試需要改 | 功能 | 本分支完成後 | 在 WSL／Linux 執行 `tests/package_gaps_test.sh`、`tests/methods_text_fetch_test.sh`、`tests/report_facts_test.sh`、`tests/where_test.sh` | 四個檔案全綠（它們的夾具都是 `accepted`，關卡放行；證明 #32／#38／#39 那批修正沒掉） | 自動：上述四個測試檔 |
| TC-G20 | 計畫「不改既有斷言」；完成標準 1 | 功能 | 對照 `origin/v3` 與本分支的 `tests/build_package_test.sh` | 逐行比對差異 | 只有『新增』的測試行（TC-G 系列）；既有斷言沒有被刪、放寬、跳過，或把預期值改成配合新輸出；`no plan`、`no runs`、`no working python`、unparseable、`--render` 沒 quarto 那幾條原樣在 | 手動：驗收者讀 diff（紀錄在 `specs/finish-accept-gate/ledger.md`） |
| TC-G21 | 完成標準 3；calibration failure 3（#39：打包修正掉了圖與註記） | 功能 | 一組全部 `accepted` 的 analysis.md 夾具：區塊格式、表格格式、含 `fig1`／`fig1_b` 前綴衝突、含空 id 列、含只有 csv 的 id | 分別用 `origin/v3` 與本分支各建一次包 | 兩邊 `submission/` 內容逐檔 `diff` 為空（時間戳除外） | 手動：executor 貼輸出到 `specs/finish-accept-gate/ledger.md`，驗收者自己重跑 |

## User Story 3 — 拒絕要發生在寫任何東西之前，且既有的拒絕順序不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-G09a | 目標第 3 點；決定一 | 例外 | 先用全部 `accepted` 的夾具建一次包成功；然後把其中一條改回 `status: proposed` | 重跑 `build_package.sh` | 結束代碼 2 | 自動：`tests/build_package_test.sh` |
| TC-G09b | 目標第 3 點（拒絕後不動既有成品） | 例外 | 同 TC-G09a，第一次建包後先備份 | 重跑被拒絕後，用 `cmp` 比對 `submission/manuscript.qmd`、`submission/report.md`、`submission/provenance.json` | 三個檔案與第一次建出來的**逐位元組相同** | 自動：`tests/build_package_test.sh` |
| TC-G09c | 目標第 3 點 | 例外 | 同 TC-G09a | 重跑被拒絕後看 `submission/` | 沒有新出現的 `report.facts.md` | 自動：`tests/build_package_test.sh` |
| TC-G10a | 決定九（`--render` 也要過關卡） | 例外 | 一條 `status: proposed` | 執行 `build_package.sh --render` | 結束代碼是 2，**不是 3**（3 是找不到 quarto） | 自動：`tests/build_package_test.sh` |
| TC-G10b | 決定九 | 例外 | 同 TC-G10a | 看錯誤輸出 | 是拒絕訊息（含 `refusing to build`），不是 quarto／Positron 缺失的訊息 | 自動：`tests/build_package_test.sh` |
| TC-G12 | 決定一（既有的 runs 檢查優先；鎖住順序） | 例外 | 一條 `status: proposed`，但專案裡**沒有 runs** | 執行 `build_package.sh` | 結束代碼 2；錯誤輸出含 `at least one run`（不是 `refusing to build`） | 自動：`tests/build_package_test.sh` |
| TC-G13 | 決定一（`pick_python` 搬家後訊息不變） | 例外 | 一條 `status: proposed`；PATH 上的 python 全是壞掉的假檔 | 執行 `build_package.sh` | 結束代碼非 0；錯誤輸出含 `no working Python on this machine` | 自動：`tests/build_package_test.sh` |
| TC-G14a | 決定八（#5 的退出碼 1 保留） | 例外 | analysis.md 只有一段自然語言（`We looked at richness and it seemed fine.`），非表格非區塊 | 執行 `build_package.sh` | 結束代碼 1；錯誤輸出含 `matched 0 plan entries` | 自動：`tests/build_package_test.sh` |
| TC-G14b | 決定八；手算範例 5 | 例外 | 同 TC-G14a | 看錯誤輸出 | **不含** `not accepted`，也沒有 `0 of 0` | 自動：`tests/build_package_test.sh` |
| TC-G22 | 決定一（`no plan` 既有行為不變） | 例外 | 專案沒有 `analysis/analysis.md` | 執行 `build_package.sh` | 結束代碼 2，沿用改動前的『找不到分析檔』訊息（既有測試的斷言不改仍綠） | 自動：`tests/build_package_test.sh`（既有 `no plan` 測試） |

## User Story 4 — 說明文字告訴人「要先接受」（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-G15a | 範圍：`skills/finish/SKILL.md` 第 1 步補一句 | 功能 | 本分支完成後 | `grep -F 'status: accepted' skills/finish/SKILL.md` | 找得到 | 自動：`tests/build_package_test.sh` |
| TC-G15b | 範圍：`docs/FINISH.md` 第 2 步補一句 | 功能 | 本分支完成後 | `grep -F 'status: accepted' docs/FINISH.md` | 找得到 | 自動：`tests/build_package_test.sh` |

## 不在範圍（計畫「不做」與裁決二明講這次不做的事）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-G23 | 不做：issue 第二個建議（成功訊息分「已組裝／可交付」、印 Results 還有幾個空位） | 不在範圍 | 全部 `accepted` 的夾具（同 TC-G06a） | 執行 `build_package.sh`，看標準輸出 | 成功訊息**沒有** issue 建議的那種新字樣（不含 `still need prose`、`not yet a finished document`、`placeholder(s)`） | 自動：`tests/build_package_test.sh` |
| TC-G25 | 不做：決定五，不加 `--force` | 不在範圍 | 一條 `status: proposed` | 執行 `build_package.sh --force <專案>` | 結束代碼 2；錯誤輸出是 `unknown option`（沒有這個旗標）；`submission/` 不存在。也就是沒有旁路 | 自動：`tests/build_package_test.sh` |
| TC-G26 | 不做：決定五，不加 `--allow-unaccepted` | 不在範圍 | 一條 `status: proposed` | 執行 `build_package.sh --allow-unaccepted <專案>` | 同 TC-G25：結束代碼 2、`unknown option`、`submission/` 不存在 | 自動：`tests/build_package_test.sh` |
| TC-G27 | 不做：不檢查『圖檔存在』『Results 寫了沒』（交給既有 `[GAP: …]`） | 不在範圍 | 一條 `status: accepted`，但 `analysis/` 底下沒有對應這個 id 的圖檔 | 執行 `build_package.sh` | 不被接受關卡擋下：錯誤輸出不含 `refusing to build`、`not accepted`（缺圖由既有機制處理，行為與改動前相同） | 自動：`tests/build_package_test.sh` |
| TC-G28 | 範圍：只准改四個檔；不改 `skills/downstream/SKILL.md`、`platform/`、`analysis.md` 格式、不新增 status 的值 | 不在範圍 | 本分支完成後 | `git diff --stat origin/v3...HEAD`（加上未提交的變更） | 變動的檔案只有 `scripts/build_package.sh`、`tests/build_package_test.sh`、`skills/finish/SKILL.md`、`docs/FINISH.md`（外加 `specs/finish-accept-gate/` 下的紀錄檔）；`skills/finish/SKILL.md` 與 `docs/FINISH.md` 各只多一句 | 手動：驗收者讀 diff（`git diff --stat` 貼進 PR 說明） |

## 憲法與安全網

這個關卡**不屬於** Safety Net 清單（計畫決定：放在 `build_package.sh`，不動 `hooks/`、不動憲法），但它搬動了 `pick_python`／`mkdir` 並動到產出文件的腳本，所以要證明原則 9 與腳本標頭沒被削弱。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-C01 | 原則 9（缺口要看得見、寫出來的東西要指回檔案） | 功能 | 本分支完成後 | 在 WSL／Linux 執行 `tests/principle_9_test.sh` | 全綠；`build_package.sh` 仍含 `no figure file starting with`、`no plan entry claims it`、`trace to a file or to a script`，且不含程式區塊標記 ```` ```{ ```` | 自動：`tests/principle_9_test.sh` |
| TC-C02 | 腳本標頭（`-h` 印的第 2–12 行不動；`TC-040` 的前 45 行限制） | 功能 | 本分支完成後 | 執行 `build_package.sh -h`，並跑 `tests/build_package_test.sh` 的 `TC-040` | `-h` 輸出的第一行仍是 `Assemble one project into something that can be sent somewhere.`，並含 `build_package.sh [--render] <project-dir>`；`TC-040` 仍綠 | 自動：`tests/build_package_test.sh` |
| TC-C03 | Safety Net／憲法：不碰 `hooks/`、不改憲法 | 不在範圍 | 本分支完成後 | `git diff --stat origin/v3...HEAD -- hooks .specify/memory/constitution.md` | 沒有任何差異；也沒有 `hooks/confirm_finish.sh` 這個檔 | 手動：驗收者讀 diff |

<!--
Rules for the writer:
- A TC tests one thing. IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
