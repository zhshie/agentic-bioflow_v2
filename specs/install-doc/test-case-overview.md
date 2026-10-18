# 測試案例總覽：docs/INSTALL.md（把 Claude Code、Claude Desktop、Codex 接上 abf 平台的說明文件）

狀態：合約已確認（2026-10-18，verifier）

**規格**：`specs/install-doc/plan.md`（沒有 spec.md）　**明細**：`test-case.md`

## 一眼看完

| 區塊 | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| 區 A — 文件測試本身 | 7 | 4 | 0 | 11 |
| 區 B — 文件內容 | 11 | 2 | 0 | 13 |
| 區 C — 不在範圍 | 0 | 0 | 7 | 7 |
| 憲法與安全網 | 0 | 4 | 0 | 4 |
| **合計** | 18 | 10 | 7 | 35 |

自動驗證 8 條（TC-001、002、003、005、007、009、011，以及 TC-013 的「出現 `abf-platform pat new`」部分）、手動驗證 27 條（TC-013 半自動半手動，計入自動）。

## 請你判斷的三件事

1. **每條是不是你要的？** 有沒有哪條的「預期結果」跟你想的不一樣。
2. **有沒有漏掉的出錯情況？** 想像實驗室成員會怎麼用錯它。
3. **「不在範圍」對嗎？** 這次不做的事，有沒有其實這次就該做的。

## 覆蓋檢查

- 計畫的需求：Test 五點（TC-001～011）、Content 六節（TC-002、012～024）全部都有測試案例：是
- 計畫沒有 User Story 與驗收情境；沒有維護者逐字範例（計畫只引 issue #93 的決定「使用者只加一個 MCP 網址、不需別的；第一批 Claude Desktop、Claude Code、Codex」，對應 TC-017、014、020）：全部有案例：是
- 計畫「Out of scope」共 7 條（不寫程式、不做套件檔、不改 CHANGELOG.md、PLATFORM.md、MIGRATION.md、TESTING.md、README），全部都有「不在範圍」測試案例（TC-025～031）：是
- 憲法：憑證規則（TC-032、033）、確認通道（TC-034）、無個人路徑（TC-035）：有案例

## 計畫審查結果

計畫無阻擋問題。三點非阻擋的觀察，已在案例裡處理：

- 計畫第 2 點說 `ask` 規則「只有倉庫真的有才寫，否則放 Not built yet」。我查到 `extensions/claude-code-kit/settings.json` 已存在（`docs/PLATFORM.md` 第 398 行、`docs/TESTING.md` 第 301 行也寫了），所以這條屬於「已有」：TC-015 要求寫進 Claude Code 一節，TC-016 要求不可列進 Not built yet。
- 計畫第 5 點「正確的空答案長什麼樣」沒寫確切內容。TC-022 只採用程式裡查得到的事實（`actions/__init__.py:72-76`：沒有 run 時回 `{"runs": []}`；經 HTTP 呼叫只列該使用者自己發起的 run），沒有另外發明。
- Claude Desktop 一節的 OAuth 流程只有 `docs/PLATFORM.md` 與 `platform/abf_platform/oauth.py` 為據，且 PLATFORM.md／TESTING.md 寫明端對端要等公開 https 網址才能實測。TC-019 要求文件如實交代，不宣稱已測過。

## 我（撰寫者）不確定的地方

1. 六個標題的確切字樣計畫只給了描述。TC-002 取計畫 Content 的主題名（What you need／Claude Code／Claude Desktop／Codex／Check it works／Not built yet），以開頭文字比對（可帶編號），字樣由實作者在測試裡固定。這樣可以嗎？
2. 「反引號裡哪些算 MCP 工具名」「哪些算看起來像檔案的路徑」計畫沒說判定規則（反引號裡也會有指令、`mcp__abf-platform__launch` 這種用戶端權限名、`claude_desktop_config.json`、網址）。實作者必須在測試裡明寫判定規則；規則太寬鬆會讓 TC-005／TC-007 形同虛設，驗收時會以 TC-006、TC-008 的假名實測。這樣可以嗎？
3. 手動案例的步驟照規則應寫在 `docs/TESTING.md` 的手動部分，但計畫明令不改 TESTING.md。驗收時我會直接讀文件與 diff 逐條對照，不要求 TESTING.md 新增步驟。這樣可以嗎？
4. Codex 一節若在實作時發現倉庫其實已有 Codex 專用檔案，TC-020 允許改寫成該檔案真有的內容；契約階段我查到沒有，所以預期是一段「Not built yet」。

## 核可紀錄

<!-- 尚無維護者核可；本狀態為 verifier 合約確認。 -->
