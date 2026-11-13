# studio-embed：下游階段把 RStudio 嵌進網頁

狀態：計畫（lead，2026-11-13）。風險 L（改下游頁的 CSP、新增一個部署設定、`deploy/` 新增一個 unit 範本）。
依據：ADR 0010「Decided」第 3 點（Studio 畫面＝嵌入 agent 那台機器自己的 localhost，附「在新分頁開啟」作退路；平台不代理任何 Studio 流量）、ADR 0011 第 4 點（下游的主畫面是 RStudio）。`studios-new-tab` 與 `cli-fetch-publish-figure` 是到目前為止的退路版。

## 維護者原話（2026-11-13）

- 「現在的規劃是R studio是使用這要自己額外裝在電腦、自己打開軟體嗎? 如果是這樣可能有點偏離我的方向，我希望他是內嵌在網頁，或是網頁能夠協助跳出R studio視窗。另外，使用者該如何檢視圖片? 至少要能夠在R studio介面好好看到圖片」
- lead 提出：改成網頁內嵌；先做只有他自己能用的版本；現有「自己裝＋打指令」那條路留著、網頁上改成次要說明。他答：「好的，4. 都按照你的建議」。
- 「我今天就要得到結果。」

## 做什麼

1. **設定**：平台多讀一個部署設定 `ABF_STUDIO_URL`（環境變數，與 `ABF_PUBLIC_URL` 同一個 env 檔）。只接受 loopback 的 http 位址加埠（`http://127.0.0.1:<埠>` 或 `http://localhost:<埠>`，沒有路徑、查詢、帳密）；其他值在啟動時拒絕並說明。未設定時，下游頁與今天完全相同（逐位元組）。
   - 位址是 loopback 的意思是：每位使用者的瀏覽器連的是**他自己那台電腦**上的 RStudio。平台不連它、不代理它、不檢查它。
2. **下游頁**（成功的分析、設定存在時）：
   - 主畫面是一個 `<iframe>`，來源是該設定位址，有標題文字；上方一行說明與一個「在新分頁開啟 RStudio」連結（`target="_blank" rel="noopener noreferrer"`）。
   - 一句說明嵌入畫面空白時怎麼辦（RStudio 沒在這台電腦上啟動，或瀏覽器擋下本機連線：請按「在新分頁開啟」，或照 `docs/` 的步驟啟動）。
   - 兩行可複製、貼進 RStudio Console 的 R 指令，已帶入這個分析的 id：一行抓結果表並載入，一行把畫好的圖送回圖庫。現有的終端機指令區塊保留，移到次要位置（`<details>` 收合）。
   - 這一頁的 CSP 只多 `frame-src <該位址>`；其他頁面的 CSP 一字不動。iframe 帶 Chromium 本機網路閘需要的 `allow` 屬性。頁面不加腳本。
   - 這一頁不自動重整（今天已是如此）；若 `live-sync` 之後併入，這一頁不得帶它的腳本，iframe 不得被替換。
3. **命令列**：`abf-platform fetch-results <run> --r` 只印 R 程式（給上面那一行用 `eval(parse(text=system2(...)))` 接）；不加 `--r` 的行為不變。送圖沿用既有的 `publish-figure`，不改它的行為（存入仍要本人在確認頁按）。
4. **部署**：`deploy/systemd/abf-rstudio.service.in`，以使用者身分（不是 root）啟動 RStudio Server：只聽 `127.0.0.1`、埠與 `ABF_STUDIO_URL` 相同、允許被 `ABF_PUBLIC_URL` 這個來源嵌入、不需另外登入（單人、僅本機）。unit 開頭照慣例寫明它不是什麼。`docs/OPERATIONS.md` 桌機一節加一步（安裝、啟用、怎麼看狀態、怎麼停、怎麼移除），並寫明：任何能登入這台電腦的人與這台電腦上的任何程式都連得到它，所以只適合個人電腦；不得把這個埠對外公開；RStudio Server 是 AGPL，本專案不隨附、不修改，由使用者自己安裝（ADR 0010 Decided 第 4 點）。
5. **文件**：`docs/PLATFORM.md`（下游頁、設定、CSP 例外）、`docs/TESTING.md`（手動步驟：三種瀏覽器各試一次嵌入；看得到 Plots 窗格的圖；貼兩行指令；空白時的退路）、`CHANGELOG.md`。

## 不做

- 平台不啟動、不停止、不代理、不探測 RStudio；不改 `platform/abf_station/`（agent 在心跳回報位址的那一半留待之後）。
- 不做 Jupyter；不做每位使用者各自的位址設定（之後另案）；不做網頁終端機（ADR 0011 第 4 點的其餘部分，另案）。
- 不碰 `.github/`、`hooks/`、憲法、`plugin.json`、`confirm.py`、`store.py`；不新增相依；不新增 CSS（樣式雜湊被釘住）——若 iframe 沒有既有 class 可用而必須加樣式，停手回報。
- 不隨附 RStudio Server 的任何檔案。

## 驗收以此為準（例子）

1. 桌機已啟動 RStudio、設定已填 → 開成功分析的下游頁，頁面中間就是 RStudio；在裡面畫圖，圖出現在右下 Plots 窗格。
2. 貼第一行指令 → 結果表載入，`View()` 看得到。貼第二行 → 得到一個確認連結，按下後圖出現在圖庫。
3. RStudio 沒啟動 → 頁面仍正常顯示，說明文字告訴我怎麼辦，「在新分頁開啟」連結在。
4. 沒填設定 → 下游頁和今天一模一樣。
5. 設定填成外部網址 → 平台拒絕啟動並說明原因；任何情況下頁面都不會嵌入 loopback 以外的位址。
6. 其他頁面（看板、確認頁、完成頁）的 CSP 沒有 `frame-src`。

## 測試怎麼做

- 先寫會失敗的測試：設定驗證、頁面結構、CSP 範圍、未設定時逐位元組相同、`--r` 輸出可被 R 解析的形狀（不需真的跑 R）、unit 範本的靜態檢查（不是 root、只聽 127.0.0.1、沒有權杖）。
- 例 1、2 的嵌入與畫圖是人工項（需要真的 RStudio 與瀏覽器），步驟寫進 `docs/TESTING.md`；lead 會在維護者的桌機上先試一次，結果寫進 ledger。嵌入若被瀏覽器擋下，退路是「在新分頁開啟」，不算失敗，但要在 ledger 寫明哪個瀏覽器、什麼訊息。
- L 級證明寫進 ledger：CSP 前後對照、設定值每個被拒絕的形狀、`git diff --stat`。
- 全套以 PR 上的 CI 為準。

## 裁決（lead，2026-11-13，回應 verifier 的五個開放點）

1. 設定由 `cmd_web` 直接讀環境變數 `ABF_STUDIO_URL`（在 `--public-url` 檢查之後、`create_app` 之前），不新增命令列旗標，`abf-web.service.in` 不改。純函式的驗證器放 `web_downstream.py`（該檔不得 import `os`）。
2. 範例埠用 8790（8787–8789 是平台自己的）。
3. 埠只寫一處：`abf-rstudio.service.in` 用 `/bin/sh -c` 從 `ABF_STUDIO_URL` 取出埠，不新增第二個變數；`ABF_STUDIO_URL` 沒填時這個 unit 以清楚的訊息結束、不重試。
4. 結尾多一個 `/` 的位址：拒絕。
5. 設定有填時，下游頁不顯示「貼上自己 Studio 網址」的表單與它的連結（`?studio=` 的值不進任何連結、iframe 或 CSP；壞值照今天顯示錯誤）；設定沒填時表單與今天完全相同。
6. 第二行 R 指令：只用基本 R，把目前的圖複製成暫存 png（`dev.copy` 到 `png`、`dev.off`），再以 `system2` 呼叫 `publish-figure <id> <該檔>`；不帶 `--code`。
7. ADR 0010 的三瀏覽器試驗：以人工 TC-036–040 與 ledger 為書面結果，由 lead 在維護者桌機上於合併前做；`rserver` 非 root 啟動實際需要哪些選項（資料目錄、cookie 金鑰檔、資料庫設定、`www-same-site`）以桌機試驗為準，executor 先照套件字串裡看得到的選項名稱寫，並在 ledger 標明未驗證處，lead 試驗後回頭修。與 ADR 0010 Decided 3 的差異（頁面不探測位址、agent 不在心跳回報）寫進 PR 說明。
