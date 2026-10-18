# 測試案例：docs/MIGRATION.md（v2 搬到 v3 的說明文件，issue #119 第 7 項）

**規格**：`specs/migration-doc/plan.md`（此功能沒有 spec.md，計畫即依據；維護者指示：測試案例只能來自計畫裡寫的事，不替它發明預期行為）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

說明：這次只交付一份文件加一支文件測試，沒有 User Story。下面依計畫的「Test」與「Content」分區。「key」指設定檔裡的設定項名稱（例如 `reach`、`workspace_id`）；「子指令」指 `abf-platform` 後面接的字（例如 `pat new`）。

## 區 A — 文件測試本身（計畫「Test (write first)」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 Test 第 1 點 | 功能 | 實作完成 | 跑 `tests/migration_doc_test.sh` | 檔案 `docs/MIGRATION.md` 存在；不存在時測試失敗並說明檔案不在 | 自動：`tests/migration_doc_test.sh` |
| TC-002 | 計畫 Test 第 1 點；Content 1–6 | 功能 | `docs/MIGRATION.md` 存在 | 跑同一支測試 | 文件有六個標題，順序與計畫 Content 1 到 6 一致：誰該讀與什麼改變、逐步、Seqera 欄位、既有的 run 與專案資料夾、退回 v2、Not built yet；少一個或順序錯就失敗 | 自動：`tests/migration_doc_test.sh` |
| TC-003 | 計畫 Test 第 2 點 | 功能 | 文件第 2、3 節用反引號寫了設定 key | 跑同一支測試 | 這兩節裡每一個被當成設定 key 的反引號名稱，都能在 `docs/SETTINGS.md` 或 `scripts/settings.sh` 找到；找不到的那個名字會被測試點名並失敗 | 自動：`tests/migration_doc_test.sh` |
| TC-004 | 計畫 Test 第 2 點（「so it cannot invent keys」） | 例外 | 在暫存副本的第 2 節加一個兩份來源都沒有的假 key（例如 `platform_url_fake`） | 對這份副本跑檢查 | 檢查失敗並點名假 key；若仍通過，表示這個檢查擋不住捏造，整支測試無效 | 手動：驗收者在暫存副本上執行，不改倉庫檔案 |
| TC-005 | 計畫 Test 第 3 點 | 功能 | 文件裡寫了 `abf-platform <子指令>` | 跑同一支測試 | 文件中出現的每一個 `abf-platform` 子指令，都存在於 `platform/abf_platform/cli.py`；不存在的會被點名並失敗 | 自動：`tests/migration_doc_test.sh` |
| TC-006 | 計畫 Test 第 3 點 | 例外 | 在暫存副本加一行 `abf-platform frobnicate`（cli.py 沒有） | 對這份副本跑檢查 | 檢查失敗並點名 `frobnicate`；若通過，表示這個檢查擋不住捏造的指令 | 手動：驗收者在暫存副本上執行，不改倉庫檔案 |

## 區 B — 文件內容（計畫「Content」1–6）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-007 | Content 1 | 功能 | 文件存在 | 讀第 1 節 | 寫明這份文件給誰（從 v2 搬到 v3 的人），並說清楚改變：v2 是外掛加 Seqera Platform，v3 是外掛透過 MCP 對自架的 abf 平台說話；內容與 `docs/adr/0001`、`0004`、`0006`、`docs/SETTINGS.md` 一致，沒有與它們矛盾的說法 | 手動：驗收者讀文件對照四份來源 |
| TC-008 | Content 2；issue 規則「keep the settings file」 | 功能 | 文件存在 | 讀第 2 節 | 明白告訴 v2 使用者：原有的設定檔照舊保留、不必重寫或搬動；沒有要求刪掉或重建 | 手動：驗收者讀第 2 節 |
| TC-009 | Content 2（「how to get a PAT (`abf-platform pat new`)」） | 功能 | 文件存在 | 讀第 2 節 | 第 2 節寫出 `abf-platform pat new` 作為取得個人存取權杖（PAT）的方式；這個指令在 `cli.py` 有（見 TC-005） | 自動：`tests/migration_doc_test.sh` |
| TC-010 | Content 2（加上平台網址與 PAT，key 名稱用程式真的讀的）；Not built yet 的條件句 | 功能 | 撰寫時以 grep `scripts/settings.sh`、`docs/SETTINGS.md`、`platform/` 查插件端有沒有「平台網址／PAT」的設定 key。契約階段已查：目前沒有這樣的 key（`docs/SETTINGS.md` 的 key 表沒有；PAT 現行用法是 `docs/PLATFORM.md` 第 4 節的 MCP 用戶端 header） | 讀第 2 節與第 6 節 | 第 2 節說清楚平台網址與 PAT 現在怎麼交給用戶端，且不使用任何捏造的 key 名；第 6 節明白寫出「插件端尚無平台網址／PAT 的設定 key」。若撰寫時發現確有此 key，則第 2 節必須用與程式完全相同的名稱 | 手動：驗收者重跑 grep 並對照第 2、6 節 |
| TC-011 | Content 3（Seqera 欄位變成選填） | 功能 | 文件存在 | 讀第 3 節 | 明白說 Seqera 相關欄位現在是選填；不說它們被移除，也不說它們必填 | 手動：驗收者讀第 3 節 |
| TC-012 | Content 3（「what still uses them, from the code」） | 功能 | 文件存在 | 讀第 3 節，對照 `scripts/` 與 `skills/` 的程式 | 文中列出仍會用到 Seqera 欄位的地方（例如 `seqera_user`、`workspace_id`、`compute_env`、`tw_bin`、`.seqera_token`），每一項都能指到程式裡真的讀它的位置；沒有程式依據的說法算失敗 | 手動：驗收者逐項對照程式 |
| TC-013 | Content 4 | 功能 | 文件存在 | 讀第 4 節，對照 `docs/PLATFORM.md` 與 `platform/abf_platform/rebuild.py` | 說明既有的 run 與專案資料夾哪些會帶過去、哪些不會；每個說法都能在 PLATFORM.md 或 `rebuild.py` 找到依據（例如 `rebuild` 從 Nextflow 自己的紀錄重建索引、不開 token 檔） | 手動：驗收者逐句對照 |
| TC-014 | Content 5 | 功能 | 文件存在 | 讀第 5 節 | 有具體的退回 v2 做法；文中提到的分支、版本或指令都真實存在（例如 `docs/ROADMAP.md` 寫 `main` 是 v2 線、v3 在分支 `v3`）；不能只是空段落 | 手動：驗收者讀第 5 節並核對提到的名稱 |
| TC-015 | Content 6 | 功能 | 文件存在 | 讀第 6 節 | 列出尚未做好的事（至少含 TC-010 說的平台網址／PAT 設定 key 缺口），每項都確實尚未存在；不把已經存在的功能列成未做 | 手動：驗收者讀第 6 節並對照程式 |

## 區 C — 不在範圍（計畫「Out of scope」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 計畫「No code」 | 不在範圍 | 實作完成 | `git diff main...HEAD --stat` | 只新增 `docs/MIGRATION.md`、`tests/migration_doc_test.sh` 與 `specs/migration-doc/` 底下的檔案；沒有改動 `scripts/`、`platform/`、`hooks/`、`skills/` 等程式 | 手動：驗收者看 diff |
| TC-017 | 計畫「Do not edit CHANGELOG.md」 | 不在範圍 | 實作完成 | `git diff main...HEAD -- CHANGELOG.md` | 無任何差異 | 手動：驗收者看 diff |
| TC-018 | 計畫「Do not edit docs/PLATFORM.md」 | 不在範圍 | 實作完成 | `git diff main...HEAD -- docs/PLATFORM.md` | 無任何差異 | 手動：驗收者看 diff |
| TC-019 | 計畫「Do not edit ROADMAP.md」 | 不在範圍 | 實作完成 | `git diff main...HEAD -- docs/ROADMAP.md` | 無任何差異 | 手動：驗收者看 diff |
| TC-020 | 計畫「Do not edit SETTINGS.md」 | 不在範圍 | 實作完成 | `git diff main...HEAD -- docs/SETTINGS.md` | 無任何差異 | 手動：驗收者看 diff |

## 憲法與安全網

這份文件會教人處理 PAT（等同密碼的長字串），所以碰到憲法 Safety Net 的憑證規則（憑證只放在部署自己的設定區、不進 git、不被印出）與第 I 條關於權杖要放在 AI 讀不到之處的說明。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | Safety Net 憑證規則（不印出、不進 git） | 例外 | 文件存在 | 在 `docs/MIGRATION.md` 搜尋 `abf_pat_` | 只出現佔位寫法（如 `<PAT>`、`abf_pat_...`），沒有任何看起來像真的權杖（`abf_pat_` 後接一長串字元） | 手動：驗收者搜尋文件 |
| TC-022 | 第 I 條：權杖要放在 AI 讀不到的地方；Safety Net 憑證規則 | 例外 | 文件存在 | 讀第 2 節關於 PAT 的指示 | 沒有叫使用者把 PAT 貼進對話、寫進會進 git 的檔案或 params 檔 | 手動：驗收者讀第 2 節 |

<!--
Rules for the writer:
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
