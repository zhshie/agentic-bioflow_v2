# 在自己的電腦上用 RStudio Desktop（過渡做法，草稿）

> **請先讀這一段。**
> 這是**過渡做法**，**不是**維護者想要的最終目標（把 RStudio 直接嵌在網頁裡）。
> 「嵌在網頁裡的 RStudio」與「到處都能跑（run anywhere）」是之後另外的卡片，這份文件不處理它們。
> 另外，「網頁內嵌 RStudio」至今只在桌機上用**無頭 Chromium（自動化）**驗證過；**真正的 Chrome 視窗、Firefox、Safari 都沒有人實際驗證過**（維護者的試用還沒回報）。
>
> 狀態：**草稿，沒有任何人照這份文件完整走過一遍。** 文中凡是寫「未驗證」的地方，都是只從程式碼推論、沒有實機測過。
> 本文是依據 `docs/PLATFORM.md`（「Commands on your own computer」與「RStudio in the downstream page」）、
> `docs/OPERATIONS.md`（「Giving a person the commands for their own computer」）以及 `platform/abf_platform/` 的程式碼寫成。

## 這份文件要做到什麼

你已經在平台上跑完一個分析（狀態 SUCCEEDED）。你想在**自己的電腦**上用普通的 RStudio Desktop 做兩件事，
就是平台「下游」頁面上那兩行 R 指令：

1. 把這次分析的結果表格載入 R。
2. 把你在 RStudio 畫好的圖，送回平台的圖庫（只是「提出申請」，最後仍要你自己到確認頁按下按鈕）。

## 安全規則（必須遵守）

1. 沒有登入的 RStudio 只能聽 `127.0.0.1`，絕不能聽 `0.0.0.0`，也絕不能透過 `tailscale serve`/`funnel`、反向代理（reverse proxy）或連接埠轉發（port forwarding）讓別人連到。
2. 只裝在「只有你一個人使用」的電腦，不裝在共用的實驗室工作站或登入節點（login node）。
3. 每個人、每台電腦各用一把自己的個人權杖（personal token），絕不分享，絕不貼進聊天、電子郵件或共用文件；電腦遺失或人員離開時要撤銷（revoke）。權杖的交付方式：由管理員當面讓你本人從螢幕上抄或貼，或用密碼管理器的分享功能。**目前沒有其他安全的遠端交付方式**（見文末「還沒驗證的事」）。
4. 平台無法遠端替你安裝軟體。

關於資料：2026-11-13，維護者被問到「分析結果會被下載到同事的個人電腦，資料可以離開平台到個人電腦嗎？」，他選了「可以，沒有不能下載的類型」（經 Sonnet 小修 session 的提問轉述，不是他自己寫的句子）。
這個回答只談「下載到個人電腦」，**不代表可以對外分享**；要把資料或結果給實驗室以外的人，仍須另外確認。

說明：本文件的 RStudio Desktop 是在你自己的電腦上、不開任何網路連接埠給別人，所以不會違反第 1 條；
第 1 條是給「有人想自己架網頁版 RStudio Server」時看的：在正式的安裝方式（另一份文件，尚未寫）出來之前，請不要自己架。

## 你需要準備什麼

| 項目 | 說明 |
|---|---|
| R | 一般的 R（從 CRAN 下載）。 |
| RStudio Desktop | Posit 公司的免費桌面版。 |
| Python 3.10 或更新 | `abf-platform` 套件要求 `requires-python >= 3.10`（`platform/pyproject.toml`）。 |
| `abf-platform` 套件 | 命令列工具，來自本專案 `platform/` 資料夾；安裝方式是在專案的複本（clone）裡執行 `pip install ./platform`（建議用虛擬環境）。專案是私有的，要先請擁有者給你讀取權限。目前沒有別的下載方式。 |
| 你自己的個人權杖 | 由平台管理員產生（`abf-platform pat new --user <你的名字>`），只顯示一次；交付方式見安全規則第 3 條（當面或密碼管理器分享，不經聊天、郵件、共用文件）。 |
| 平台網址 | 管理員給你的 `https://...` 網址，**只要主機名稱，後面不要加路徑**。 |
| 一個 SUCCEEDED 的 run | 你自己的 run，並且平台到運算站台的連線是開著的。 |

注意：命令列工具的名字是 `abf-platform`（不是 `abf`）。

## 兩行 R 指令是什麼

平台下游頁面（`stage=downstream`）顯示這兩行，貼到 RStudio 的 Console（來源：`web_downstream._r_lines`）。
`<run id>` 是 16 個小寫十六進位字元；以頁面上顯示的那兩行為準，下面只是讓你先看懂。

```r
eval(parse(text = system2("abf-platform", c("fetch-results", shQuote("<run id>"), "--r"), stdout = TRUE)))
```

```r
local({f <- tempfile(fileext = ".png"); dev.copy(png, filename = f); invisible(dev.off()); system2("abf-platform", c("publish-figure", shQuote("<run id>"), shQuote(f)))})
```

- 第一行：叫 `abf-platform` 把這個 run 的小型結果表格抓到你電腦上的 `~/abf-results/<run id>`，並載入 R。
  只抓 `.tsv .csv .txt .md .json`，單檔上限 25 MB、最多 200 檔、總共 100 MB；網頁報告（`.html`）與二進位檔不會抓。
- 第二行：把 RStudio 目前 Plots 窗格正在顯示的圖複製成暫時的 png，提出申請送進圖庫。**它不會自己存進去**，
  會印出一個確認連結，你要用瀏覽器開那個連結、登入、按下送出，圖才會進圖庫。
- 重要：頁面是否顯示這兩行，取決於管理員有沒有設定 `ABF_STUDIO_URL`。沒設定時頁面顯示的是三行終端機指令。
  如果你的頁面沒有 R 指令，請管理員確認，或自己用上面的樣板（把 `<run id>` 換成你的 run id）。
- 這兩行靠 R 去呼叫 `abf-platform`，所以 **RStudio 必須找得到 `abf-platform`**（它所在的資料夾要在 RStudio 看得到的 `PATH` 裡）。
  最簡單的檢查：在 RStudio Console 執行 `system2("abf-platform", "--help")`，應該印出用法而不是錯誤。

## Windows

**重要：下面整段「原生 Windows」未驗證。**
從程式碼只能證明以下幾點，沒有任何一點是實機驗證過的：

- `fetch-results --r` 與 `studio-connect` 是純 Python 加 MCP 用戶端，沒有 Unix 專用的呼叫，
  所以**原則上**原生 Windows 的 Python 可以跑；但**沒有人在 Windows 上端到端跑過**。
  （`docs/TESTING.md` 的人工檢查表有 Windows 的字樣，但那是檢查表，不是已完成的結果。）
- `~/.abf/studio.json` 的權限檢查：程式碼 `permission_bits_trusted()` 只在 POSIX 系統（Linux、Mac）檢查檔案模式，
  **在 Windows 上完全不檢查，也不檢查 ACL**。也就是說在 Windows 上，程式**不會**替你擋下「別人也讀得到的設定檔」。
  它只在 `studio-connect` 時提醒一次：檔案放在你的個人資料夾，不要放到會被雲端同步的資料夾。
  所以你要**自己**檢查：執行 `icacls "%USERPROFILE%\.abf\studio.json"`，只能看到你自己（以及系統管理員／SYSTEM）。
- R 的 `system2("abf-platform", ...)` 與 `shQuote` 在 Windows 上能不能正確找到並執行 `abf-platform.exe`：**未驗證**。

如果你不想碰這些未驗證的部分，保守作法是：**Windows 請在 WSL 內做這些步驟**
（`abf-platform`、設定檔、權限檢查都在 WSL 的 Linux 裡，檔案模式檢查是有效的）。
但這樣產生兩個問題，也都**未驗證**：Windows 版 RStudio Desktop 的 `system2` 看不到 WSL 裡的 `abf-platform`
（要改成在 WSL 內另外裝 R 與 RStudio，或在 R 裡用 `wsl.exe` 呼叫）。目前沒有人試過，所以先不要把這條路當成已知可行。

**Windows 的家目錄提醒（未驗證）**：R 在 Windows 上的 `~` 是「文件」資料夾，而且常被 OneDrive 同步；`abf-platform` 用的家目錄是使用者個人資料夾（`%USERPROFILE%`），兩者不同。
程式把結果放在 `%USERPROFILE%\abf-results\<run id>`，第一行 R 指令載入表格時用的是**完整的絕對路徑**（已看程式確認：`studio_cli.py` 的 `r_snippet` 寫入的是完整路徑，不是 `~`），所以不會找錯地方。
但請你確認 `%USERPROFILE%\.abf` 與 `%USERPROFILE%\abf-results` **不在 OneDrive 或其他同步資料夾之下**，否則權杖與結果會被同步到雲端。

### 原生 Windows 的步驟（未驗證）

1. 安裝 R：到 CRAN 下載 Windows 版 R，一路按下一步。
   你應該看到：開始功能表出現 R。
2. 安裝 RStudio Desktop：從 Posit 官網下載 Windows 安裝檔並安裝。
   你應該看到：開啟 RStudio 後，左邊有 Console，輸入 `1+1` 按 Enter 得到 `[1] 2`。
3. 安裝 Python 3.10 或更新（python.org），安裝畫面勾選「Add python.exe to PATH」。
   你應該看到：在 PowerShell 執行 `python --version`，印出 3.10 或更高。
4. 取得專案複本（需要先有讀取權限）並安裝套件。在 PowerShell：
   `python -m venv abf-venv`，再 `abf-venv\Scripts\activate`，再在專案資料夾執行 `pip install ./platform`。
   你應該看到：最後出現 `Successfully installed ... abf-platform ...`；執行 `abf-platform --help` 印出用法。
5. 把 `abf-platform.exe` 所在資料夾（虛擬環境的 `Scripts`）加進 Windows 的 `PATH`，然後**完全關閉並重開 RStudio**。
   你應該看到：在 RStudio Console 執行 `system2("abf-platform", "--help")` 印出用法。
   （若看到找不到程式，代表 RStudio 看不到那個資料夾；這一步最容易出問題。未驗證。）
6. 存下你的權杖：在 PowerShell 執行 `abf-platform studio-connect --server https://<平台網址>`，
   在隱藏的提示處貼上你的個人權杖（貼上時畫面不會顯示字，這是正常的）。
   你應該看到：印出網址、「權杖已存在 <路徑>」，以及一則「不要放在雲端同步資料夾」的提醒。權杖本身不會被印出來。
7. 自己檢查設定檔權限：`icacls "%USERPROFILE%\.abf\studio.json"`（程式不會替你檢查）。
   你應該看到：只有你自己的帳號（和 SYSTEM／Administrators）。若看到 `Everyone` 或其他使用者，不要繼續，請找管理員。
8. 到平台網頁，打開你那個 SUCCEEDED run 的「下游」頁，把第一行 R 指令貼到 RStudio Console 按 Enter。
   你應該看到：Console 先印出資料夾路徑等進度訊息，接著環境（Environment）窗格出現載入的資料表；
   `~/abf-results/<run id>` 資料夾裡有檔案。
9. 在 RStudio 畫一張圖（例如 `plot(1:10)`），確認右下 Plots 窗格有圖，然後貼第二行。
   你應該看到：Console 印出一個確認連結，並說「尚未存入，請用瀏覽器開啟連結並按送出」。
10. 用瀏覽器開那個連結、登入平台、看清楚內容後按下送出。
    你應該看到：圖出現在那個 run 的圖庫。

## Mac

**未驗證（我們沒有 Mac 實機，需有同事實機試過才算完成）**

以下是依程式碼寫的步驟。Mac 屬 POSIX，程式碼會檢查設定檔模式，所以從程式碼看比 Windows 單純，但仍然**沒有人在 Mac 上跑過**。

1. 安裝 R：到 CRAN 下載 macOS 版（注意晶片是 Apple Silicon 還是 Intel，下載對應版本）。
   你應該看到：Applications 裡出現 R。
2. 安裝 RStudio Desktop：從 Posit 官網下載 macOS 版，拖進 Applications。
   你應該看到：開啟後 Console 輸入 `1+1` 得到 `[1] 2`。
3. 確認 Python 3.10 或更新：在「終端機」執行 `python3 --version`。沒有的話從 python.org 安裝。
   你應該看到：版本 3.10 或更高。
4. 取得專案複本（需要先有讀取權限），建立虛擬環境並安裝：
   `python3 -m venv ~/abf-venv`，`source ~/abf-venv/bin/activate`，在專案資料夾執行 `pip install ./platform`。
   你應該看到：`Successfully installed ... abf-platform ...`；`abf-platform --help` 印出用法。
5. 讓 RStudio 找得到 `abf-platform`。從 Dock 開啟的 RStudio 通常看不到終端機設定的 `PATH`，
   所以不要假設它會找得到；可在 RStudio 的 Console 檢查 `system2("abf-platform", "--help")`，
   找不到的話，在 `~/.Renviron` 檔加入完整的這一行（**保留原本的 PATH**，不要只寫新的路徑，否則整個 PATH 會被蓋掉）：`PATH=${PATH}:${HOME}/abf-venv/bin`，然後重開 RStudio。（未驗證）
   你應該看到：Console 印出用法，而不是 error。
6. 存下權杖：`abf-platform studio-connect --server https://<平台網址>`，在隱藏提示貼上個人權杖。
   你應該看到：印出網址與「權杖已存在 <路徑>」，權杖本身不會顯示。
7. 檢查設定檔權限：`ls -l ~/.abf/studio.json`。
   你應該看到：`-rw-------`（只有你能讀寫）。程式也會檢查：若別人讀得到，會拒絕使用並叫你執行 `chmod 600`。
8. 在平台下游頁，把第一行 R 指令貼到 RStudio Console。
   你應該看到：環境窗格出現資料表，`~/abf-results/<run id>` 有檔案。
9. 畫一張圖，確認 Plots 窗格有圖，貼第二行。
   你應該看到：Console 印出確認連結，說明尚未存入。
10. 用瀏覽器開連結、登入、按送出。
    你應該看到：圖出現在圖庫。

## 出錯時看什麼

`abf-platform` 的結束代碼（`docs/PLATFORM.md`）：

| 代碼 | 意思 | 怎麼辦 |
|---|---|---|
| 2 | 沒設定、設定檔別人讀得到（僅 Linux/Mac）、設定檔壞掉、網址或權杖不能用 | 重跑 `studio-connect` |
| 3 | 連不上：權杖錯或已被撤銷、電腦離線、平台網址沒回應 | 檢查網路；問管理員平台機器是否開著，必要時換新權杖 |
| 1 | 有東西沒抓到（站台拒絕、檔案過大、站台連線沒開、找不到 run） | 看訊息裡的原因；站台連線沒開要找管理員 |

訊息會說明發生什麼事與下一步，不會顯示權杖。權杖掉了或外洩：立刻請管理員 `abf-platform pat revoke <id>`，再領新的。

## 還沒驗證的事（給維護者）

- 原生 Windows 上 `studio-connect`、`fetch-results --r`、`publish-figure` 端到端是否可用。
- Windows 上程式不檢查設定檔的 ACL（只提醒），由使用者自己用 `icacls` 檢查。
- RStudio Desktop（Windows）的 `system2` 是否找得到 `abf-platform.exe`；以及 WSL 內裝與 Windows 版 RStudio 如何銜接。
- 整份 Mac 流程，包含 RStudio 從 Dock 開啟時的 `PATH`。
- 頁面上兩行 R 指令是否一定顯示（依賴 `ABF_STUDIO_URL`）。
- Windows 上的 `~` 與 OneDrive 同步（見 Windows 一節的提醒）。
- 權杖的遠端交付：目前沒有安全的遠端交付方式，只有當面或密碼管理器分享。
- 取得專案複本需要讀取權限，那屬於「改權限」，要維護者本人決定並親手給，平台與 AI 都不會代辦。
- 以上沒有任何一項是我們實機測過的。
