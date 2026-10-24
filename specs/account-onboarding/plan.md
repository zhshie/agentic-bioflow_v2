---
id: account-onboarding
title: 同事開帳號與上手：一份 docs/ONBOARDING.md（管理者清單＋可直接寄出的歡迎信＋國網同事裝站台代理的一頁），指令與旗標由測試核對真的存在
tier: A
kinds: docs
lane: L-onboard
base: v3（`origin/v3` @ 6061925；所有行號都是該版本）
source: developer-agent 讀碼查證（2026-10-25）；總表 H-2（replan 第 187 行）與「我自己要做的」（第 11 條，同事帳號申請說明）；上一位規劃者建議的候選
---

# account-onboarding

> 總表 H-2 原本有三件：①開帳號時設雲端月上限 ②歡迎信文字 ③同事安裝站台代理的一頁說明。**①已經做完**（`abf-platform user add --cloud-cap-usd`，`cli.py:564-569`，由 `cloud-cost` 系列合併）。剩 ②③，只是文件，所以降為 A／docs。歡迎信若要由 `user add` 直接印出，要動 `cli.py`（排在別人後面）→ 列在「不做」與裁決 1。

## 目標
新增 `docs/ONBOARDING.md`：管理者照著開一個同事帳號、同事照著連上並（國網用戶）裝好站台代理，全程每個指令都對得上真的程式。對使用者的意義：試用成功標準是「同事不問我就能跑完一次 16S」（replan 第 17 條），這份就是「不問我」的那一半。

## 維護者原話（verifier 出題用）
- 「試用成功標準改成：同事不問我就能跑完一次 16S（零支援）」→ T1、T6（每個步驟都有指令與預期畫面，沒有「請洽管理者」式的空話）。
- 「同事帳號申請的說明（國網帳號＋加入計畫＋站台代理安裝）」（replan「我自己要做的」）→ T4、T7。
- 「雲端上限：管理者開帳號時設，使用者不能改；單位美元、不換算」（replan C-3；`cloud-cost.md` 引他 10-18／10-21 原話）→ T3、T9。
- 「國網用戶裝在個人電腦（持 2FA）；雲端用戶不裝代理」（replan 第 13 條）→ T7、T8。

## 範圍：檔案（4 個）
- `docs/ONBOARDING.md`（新）
- `README.md`（只在第 47 行 `**docs/PITFALLS.md**` 那一段前面加一段指向它，不動其他字）
- `platform/tests/test_onboarding_doc.py`（新；檔首 `# Nothing existing: …` ≥15 字，`test_scope.py:76` 檢查）
- `specs/account-onboarding/ledger.md`
- **不准動**：`docs/INSTALL.md`（`tests/install_doc_test.sh:42-59` 要求其中每個含底線的反引號詞都是 MCP 工具名、六個 `##` 標題固定）、`docs/OPERATIONS.md`、`docs/PLATFORM.md`、`docs/TESTING.md`（都在別的任務手上）、一切程式碼。

## 作法（內容決定）
`docs/ONBOARDING.md` 恰好五個 `##` 標題，依序：`## 1. Who does what`、`## 2. The operator opens the account`、`## 3. The welcome message`、`## 4. The colleague connects`、`## 5. A colleague on NCHC runs a station agent`。英文為主，每節開頭附一句中文要點（本專案文件慣例）。
1. **§1**：兩個角色（operator＝跑平台的人；colleague）；一張表：誰在哪台機器做什麼。明說「雲端用戶不裝站台代理，國網用戶裝」（`PLATFORM.md:252` 對應句）。
2. **§2 管理者清單**，每步一個指令、一句預期結果，順序固定：
   a. `abf-platform user add <name> --lab <lab> --cloud-cap-usd <N>`（`cli.py:111-126`、`:564-569`）；沒給 `--cloud-cap-usd` 時此人**不能送到雲端**，要之後 `abf-platform user cloud-cap <name> <N>`（`cli.py:567-568`、`:570-573`）；單位美元，範圍 0 到 1,000,000（`store.py:732`）；國網不設上限。
   b. `abf-platform user passwd <name>`：**只能在真的終端機由本人輸入兩次**，沒有旗標或檔案可以代填（`cli.py:148-160`）。
   c. 依對方用的 AI app：Claude Desktop 只要網頁密碼（OAuth，`INSTALL.md:12-14`）；Claude Code 要 `abf-platform pat new --user <name>`，**只顯示一次**（`cli.py:179`、`INSTALL.md:15-19`）。PAT 要在對方自己的終端機貼，不貼進聊天。
   d. 國網同事：`abf-platform agent-token new <agent-name> --user <name>`（`cli.py:552-557`），再 `abf-platform ce create --owner <name> --agent <agent-name> …`（`cli.py:502,505`；其餘欄位指向 `docs/PLATFORM.md` 的對應節，不重抄）。
   e. 驗證：請對方照 `INSTALL.md` §5 檢查；管理者端 `abf-platform pat list` 看得到 token（不顯示值）。
3. **§3 歡迎信**：一個 fenced 區塊，可原樣複製寄出；用 `<platform-URL>`、`<name>`、`<lab>`、`<operator>` 四個佔位符，內容：平台網址、登入方式（網頁密碼／PAT 兩條）、下一步指向 §4 與 `docs/INSTALL.md`、國網用戶指向 §5、雲端上限一句（美元、由管理者設）、遇到問題先看哪份文件。**不含任何真實 token、密碼、國網帳號或計畫號**（計畫號用 `<your NSTC project>` 佔位）。
4. **§4**：指向 `docs/INSTALL.md` 的三個 app 小節（不重抄），加一段「怎麼確認連上了」：Claude 端問 `list_runs` 之類的唯讀工具（用 `INSTALL.md` §5 已有的那個工具名）。
5. **§5 國網同事**：先決條件（有國網帳號、已加入計畫、WSL 或 Linux bash；原生 Windows／Git Bash 會被拒，`abf_station/cli.py:31-36`）；步驟照 `docs/PLATFORM.md:140-171` 的順序（token 檔放 WSL 自己的 home、`chmod 600`、先用 `scripts/on_site.sh --check-reach` 印出的那一行開共用連線、再 `abf-station run --platform <platform-URL> --token-file ~/.config/abf/agent.token --deployment <root>`，旗標見 `abf_station/cli.py:145-147`）；平台網址除了 `localhost`／`127.0.0.1` 必須是 https（`abf_station/cli.py:38-45`）；「怎麼知道它活著」：問 `list_agents`（`PLATFORM.md:171`）；出錯對照表只連到 `PLATFORM.md` 的「What it tells you」，不重抄。
6. `README.md`：在第 47 行前加 `**docs/ONBOARDING.md** — opening an account for a colleague, the welcome message, and a colleague's first connection.` 一段，前後各空一行。

## 失敗先行測試（`test_onboarding_doc.py`；比照 `tests/operations_doc_test.sh`、`tests/install_doc_test.sh` 的做法，用 Python 寫）
| 編號 | 案例 | 預期 | 現況 |
|---|---|---|---|
| T1 | `docs/ONBOARDING.md` 存在、恰好五個 `## ` 標題且依序符合 §1…§5 的關鍵字 | 全符 | 紅 |
| T2 | 文中每個 `abf-platform <w1> [<w2>]` 的 `w1` 是 `cli.py` 的 `sub.add_parser("<w1>"` 之一；`w1` 為 `user`／`pat`／`agent-token`／`ce` 時 `w2` 也是 | 全存在 | 紅 |
| T3 | 文中出現的旗標 `--lab`、`--cloud-cap-usd`、`--user`、`--owner`、`--agent` 都在 `cli.py` 的 `add_argument` 裡 | 全存在 | 紅 |
| T4 | 文中每個 `abf-station <w>` 的 `w` 是 `abf_station/cli.py` 的子指令；旗標 `--platform`、`--token-file`、`--deployment` 都在 `abf_station/cli.py:145-147` | 全存在 | 紅 |
| T5 | 文中反引號包的 repo 路徑（頂層目錄 `docs/`、`scripts/`、`platform/`、`deploy/`＋副檔名）都存在 | 全存在 | 紅 |
| T6 | 歡迎信區塊含四個佔位符 `<platform-URL>`、`<name>`、`<lab>`、`<operator>`，且含 §2、§4、§5 的指向 | 全含 | 紅 |
| T7 | §5 含 `chmod 600`、`--check-reach`、`list_agents`、`https`，且 `list_agents` 是 `mcp_server.py` 的工具名 | 全含 | 紅 |
| T8 | §1 或 §5 明寫雲端用戶不裝站台代理（含 `Google Batch` 與 `install nothing` 之類句子，措辭由 executor 定，測試查關鍵字 `Google Batch` 與 `no station agent` 或 `install nothing`） | 含 | 紅 |
| T9 | 文中不含 `NT$`、`台幣`、`匯率`（上限只用美元）；含 `US$` 或 `US dollars` | 符合 | 紅 |
| T10 | 文中不含形似 PAT 的字串（`abf_pat_[A-Za-z0-9]{8,}`）、不含 `mst1\d{5}`（計畫號）、不含 `u9\d{7}`（國網帳號形狀） | 無命中 | 紅 |
| T11 | `README.md` 含一行指向 `docs/ONBOARDING.md`，且該行在 `docs/PITFALLS.md` 那段之前；其他行與 base 逐字相同 | 符合 | 紅 |
| T12 | 變異測試：把一份複製的文件裡 `user cloud-cap` 改成 `user cloudcap`、`--cloud-cap-usd` 改成 `--cloud-cap`，用同一組檢查函式 | T2、T3 各抓到 | 紅 |
| T13 | `docs/INSTALL.md` 與 `docs/OPERATIONS.md` 位元組不變（比對 `git diff --stat` 證據貼 ledger；測試端只查兩檔仍通過各自的既有 doc 測試） | 通過 | 綠（鎖住） |

**會改斷言的既有測試：無。** 必須仍綠：`tests/install_doc_test.sh`、`tests/operations_doc_test.sh`、`platform/tests/test_cloud_wire.py:411`（掃 `docs/`、`README.md`，不得含「還沒有費用預估與上限」「接線之前確認畫面仍寫」）、`tests/constitution_scope_test.sh:67,73`（README 仍含 `Constitution 2.0.0`，且不得出現「safety net … every session」類字樣）、`tests/platform_direction_docs_test.sh:386-392,537`（README 既有字串）、`tests/no_hardcoded_paths.sh`（掃 README：不得出現 `/home/<名>/` 形狀）、`tests/works_without_host_test.sh:92`（文件裡的 `scripts/…` 路徑必須存在）。

## 完成標準（done when）
- T1–T13 全綠；`bash tests/run_all.sh`（WSL）綠。
- `git diff --name-only` 只含上列 4 個檔；`README.md` 只多出一段。
- 文件裡每個指令一行一個，沒有「略」「同上」。

## 環境事實
- `user add` 的提示（`cli.py:126`）是「issue a token with: abf-platform pat new --user …」，沒有歡迎信；沒給上限時 `--help` 已寫「cannot send to the cloud until you run: user cloud-cap」（`cli.py:567-568`）。
- 操作手冊 §5 的指令表（`OPERATIONS.md:107-126`）是給管理者查指令用；§「Hosting one lab」第 5 步只有一句「Add the lab's people with the commands in section 5」（`OPERATIONS.md:186`）。本檔補的是「照順序做完一個人」。
- 站台代理的啟動步驟已在 `PLATFORM.md:140-171`；本檔只排順序與前置，不重寫。

## 不做
- 不改任何程式（歡迎信不印在 `user add`；那要動 `cli.py`，見裁決 1）。
- 不改 `INSTALL.md`、`OPERATIONS.md`、`PLATFORM.md`、`TESTING.md`；不寫國網帳號申請的外部流程細節（那是國網的規定，不是本專案的）。
- 不寫計畫號、帳號、token、密碼的任何真值。

## 裁決
1. **歡迎信只在文件，不由 `user add` 印出**（預設）：印出要動 `cli.py`，目前被 `dataset-cli-launch` 與 `cloud-cleanup-backfill` 佔著；若維護者要「開完帳號自動印歡迎信」，另開小任務，`after: cloud-cleanup-backfill`。
2. **`user passwd` 的實際情境待維護者答**：程式要求「本人在真的終端機輸入」（`cli.py:148-160`），託管主機上同事通常沒有 shell。文件只寫程式的事實，並在 §2b 標一句「if the person has no shell on the platform host, set it together at that host's terminal」；這句是不是你要的做法，請確認。預設如此。
3. **為什麼不放進 `INSTALL.md`**：replan 原計畫寫進該檔，但 `tests/install_doc_test.sh` 把它鎖成「六節、反引號詞必須是工具名」，且 `cloud-upload-docs.md` 也把它列為不准動。新檔是唯一不改測試的做法。
4. **語言**：英文為主＋每節一句中文要點；若維護者要同事收到純中文歡迎信，§3 的區塊改雙語兩份，其餘不變。

## 裁決（2026-10-25 00:40，developer-agent）
1. 寫成新檔 `docs/ONBOARDING.md`，README 加一段指標；不動 INSTALL.md。
2. `user passwd` 只寫程式實際行為，加一行標註「遠端同事怎麼設密碼：待維護者決定」；`user add` 的歡迎文字不在本片。

## 專長守則（docs）

（工作區沒有 `.claude/dev-profiles/docs.md`；本任務無專長守則。）
