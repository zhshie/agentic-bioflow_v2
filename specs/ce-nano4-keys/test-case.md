# 測試案例：計算環境新增 modules／siteConfigVars／sitePipelines 三鍵（ce-nano4-keys，M1-01）

**規格**：`specs/ce-nano4-keys/plan.md`（本任務沒有 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

出題依據：計畫本身、維護者 10-21 裁示 3 的原話、計畫列出的兩支失敗先行測試。計畫沒寫的行為不出題（疑點見總覽）。

**需求編號**（本檔自編，方便對照，出自計畫的哪一段就標哪一段）：

- R1 `modules` 規則（作法第 1 點）
- R2 `siteConfigVars` 規則（作法第 2 點）
- R3 `sitePipelines` 規則（作法第 3 點）
- R4 逐鍵驗證，錯誤訊息點名鍵名與壞值，一次列出全部錯誤（作法）
- R5 `view()` 原樣回傳三鍵，不展開、不改序（作法）
- R6 `credential_findings` 照掃三鍵的字串（作法）
- R7 既有 CE 沒有三鍵則行為完全不變（作法）
- R8 不需要 migration，並在 ledger 寫明核對結果（作法）
- R9 兩支失敗先行測試，既有 test_tc024／test_tc029 系列不得改動（失敗先行測試）
- R10 完成標準：`ce create` 能存含三鍵的 slurm-platform 列、壞值被點名拒絕、全套測試綠
- R11 不做：不改站台、不改 `su.py`、不建 nano4 的實際 CE JSON（不做）
- R12 不加 `preRunScript`／`postRunScript` 的新處理（不做）
- R13 維護者原話：借國網零件自己啟動（`$NFCORE_<P>_HOME`、`$NFCORE_SITE_CONFIG`、`$NFCORE_SITE_REFERENCES`），缺 module 退回 `owner/name -r rev`
- R14 專長守則（backend）

計畫指定的兩支測試名稱對應：`test_tc024b_nano4_keys_are_stored_field_by_field` 對應 TC-NK-01；`test_tc029b_modules_and_site_pipelines_refuse_shell_shapes` 對應 TC-NK-06～08、TC-NK-11。每條自動測試要在註解寫上自己的 TC 編號（例如 `# TC-NK-06`）。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

名詞：「CE」＝計算環境（Compute Environment，系統裡描述一個叢集怎麼用的設定）；「三鍵」＝ `modules`、`siteConfigVars`、`sitePipelines` 這三個新設定；「被拒」＝指令結束碼不是 0，畫面上有拒絕原因，且資料庫一個位元組都沒變。

以下步驟裡的「建立」一律指 `abf-platform ce create --name … --platform slurm-platform --work-dir=/data/work --head-queue=normal --config-json '…'`，「更新」指 `abf-platform ce update <名字> --config-json '…'`，「查看」指 `abf-platform ce show <名字>`。

## User Story 1 — 站台描述能存進去、讀得回來（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-NK-01 | R1、R2、R3、R5、R13；計畫測試 tc024b | 功能 | 空的平台。以維護者原話裡的名字當輸入：modules＝`["biology/Nextflow/26.10.0","biology/nf-core-ampliseq/2.18.0"]`；siteConfigVars＝`["NFCORE_SITE_CONFIG","NFCORE_SITE_REFERENCES"]`；sitePipelines＝`[{"pipeline":"nf-core/ampliseq","revision":"2.18.0","module":"biology/nf-core-ampliseq/2.18.0","home":"NFCORE_AMPLISEQ_HOME"}]` | 建立一個含這三鍵的 slurm-platform CE，再查看 | 建立成功（結束碼 0）。查看到的設定裡，三鍵的每一項都與送進去的完全相同（逐項相等：兩個 module、兩個變數名、sitePipelines 那一項的四個欄位 pipeline／revision／module／home），沒有多出別的欄位；原有欄位（workDir、headQueue）照舊 | 自動：`platform/tests/test_station_envs.py`（`test_tc024b_nano4_keys_are_stored_field_by_field`） |
| TC-NK-02 | R5；US 完成標準 | 功能 | 同 TC-NK-01 建好的 CE | 用唯讀的 MCP 工具 `get_compute_env` 與 `list_compute_envs` 讀它 | 兩個工具回傳的 config 都含三鍵，內容與 TC-NK-01 送進去的逐項相同 | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-03 | R5（不改序） | 功能 | 空的平台。modules＝`["biology/nf-core-ampliseq/2.18.0","biology/Nextflow/26.10.0"]`（故意把字母順序大的放前面）；siteConfigVars＝`["NFCORE_SITE_REFERENCES","NFCORE_SITE_CONFIG"]`（同樣倒著放）；sitePipelines 放兩項，第二項的 pipeline 排序比第一項小 | 建立後查看 | 三鍵的清單順序與送進去的完全一樣（沒有被排序、去重或重排） | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-04 | R1～R3；`update` 沿用建立的規則 | 功能 | 已有一個沒有三鍵的 slurm-platform CE `lab-a` | 對 `lab-a` 更新，只帶三鍵（用 TC-NK-01 的值），再查看 | 更新成功；查看到三鍵與送入相同；`workDir`、`headQueue`、描述、代理名稱等其他欄位與更新前相同 | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-05 | R1～R3（規則不是「全部拒絕」） | 功能 | 空的平台 | 建立一個 CE，三鍵放這些合法值：module `a+b-c_d.e/1`；變數名 `_X1`；revision 為 40 個小寫十六進位字元（例如 40 個 `a`）；另一項 revision `v2.18.0` | 建立成功，查看時這些值原樣在 | 自動：`platform/tests/test_station_envs.py` |

## User Story 2 — 壞值被點名拒絕，一次列全（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-NK-06 | R1、R4；計畫測試 tc029b | 例外 | 空的平台 | 建立 CE，`modules=["a;b"]` | 被拒；拒絕原因裡出現鍵名 `modules` | 自動：`platform/tests/test_station_envs.py`（`test_tc029b_modules_and_site_pipelines_refuse_shell_shapes`） |
| TC-NK-07 | R1、R4；計畫測試 tc029b | 例外 | 空的平台 | 建立 CE，`modules=["a b"]`（中間一個空白） | 被拒；拒絕原因裡出現鍵名 `modules` | 自動：同上 |
| TC-NK-08 | R1、R4；計畫測試 tc029b | 例外 | 空的平台 | 建立 CE，`modules=["../x"]` | 被拒；拒絕原因裡出現鍵名 `modules`（註：單看允許字元的規則會放行它，計畫的測試清單明確要求要拒，見總覽疑問） | 自動：同上 |
| TC-NK-09 | R1、R4 | 例外 | 空的平台 | 逐一建立 CE，modules 的單項分別是 `$(id)`、`` `id` ``、`a\|b`、`a&b`、中間夾換行的 `a`＋換行＋`b`、空字串 | 每一次都被拒，原因裡出現鍵名 `modules` | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-10 | R2、R4 | 例外 | 空的平台 | 逐一建立 CE，siteConfigVars 的單項分別是 `NFCORE_SITE_CONFIG; id`、小寫的 `nfcore_site_config`、數字開頭的 `1ABC`、`A B`、`$(id)`、空字串 | 每一次都被拒，原因裡出現鍵名 `siteConfigVars` | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-11 | R3、R4；計畫測試 tc029b | 例外 | 空的平台 | 建立 CE，sitePipelines 一項，其他欄位合法，`home="$(id)"` | 被拒；原因裡出現 `sitePipelines[0].home` | 自動：`platform/tests/test_station_envs.py`（`test_tc029b_…`） |
| TC-NK-12 | R3、R4 | 例外 | 空的平台 | 逐一建立 CE，sitePipelines[0].home 分別是小寫的 `nfcore_home`、數字開頭的 `1ABC`、`${HOME}`、`A B`、空字串 | 每一次都被拒，原因裡出現 `sitePipelines[0].home` | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-13 | R3、R4（計畫舉的例子） | 例外 | 空的平台 | 建立 CE，sitePipelines[0].module＝`a;b`，其他欄位合法 | 被拒；原因裡同時出現 `sitePipelines[0].module` 與壞字元 `;`（計畫範例：`sitePipelines[0].module: 不允許 ';'`） | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-14 | R3、R4（pipeline 沿用 OWNER_NAME 規則） | 例外 | 空的平台 | 逐一建立 CE，sitePipelines[0].pipeline 分別是 `nf-core`（沒有斜線）、`nf-core/ampliseq/x`（兩個斜線）、`nf-core/ampliseq;id`、`a b/c` | 每一次都被拒，原因裡出現 `sitePipelines[0].pipeline` | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-15 | R3、R4（revision 沿用 REVISION 規則） | 例外 | 空的平台 | 逐一建立 CE，sitePipelines[0].revision 分別是分支名 `master`、`dev`、`2.18.0; id`、空字串 | 每一次都被拒，原因裡出現 `sitePipelines[0].revision`；而 `2.18.0`、`v2.18.0`、40 位十六進位的 revision 仍被接受（接受與拒絕的集合與專案現有 REVISION 規則一致） | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-16 | R4（索引要指對） | 例外 | 空的平台 | 建立 CE，sitePipelines 兩項，第一項全部合法，第二項的 module 含 `;` | 被拒；原因指出的是 `sitePipelines[1].module`，不是 `[0]` | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-17 | R1～R3（型別：modules／siteConfigVars 是文字清單，sitePipelines 是物件清單） | 例外 | 空的平台 | 逐一建立 CE：`modules` 給成單一文字 `"biology/Nextflow/26.10.0"`（不是清單）；`modules=[5]`（項目是數字）；`siteConfigVars` 給成單一文字；`sitePipelines=["nf-core/ampliseq"]`（項目不是物件） | 每一次都被拒，原因裡出現對應的鍵名（`modules`／`siteConfigVars`／`sitePipelines`），沒有程式崩潰的堆疊畫面 | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-18 | R4（一次列出全部錯誤） | 例外 | 空的平台 | 建立一次 CE，同時放三個壞值：`modules[0]="a;b"`、`siteConfigVars[0]="bad name"`、`sitePipelines[0].home="$(id)"` | 被拒，且同一則拒絕訊息裡同時點名三處（`modules`、`siteConfigVars`、`sitePipelines[0].home`），不是只報第一個 | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-19 | R4；專長守則（沒確認／出錯不得寫入） | 例外 | 先記下資料庫的完整位元組內容 | 做 TC-NK-06～18 中任一個會被拒的建立（至少 modules、siteConfigVars、sitePipelines 各一個） | 每次被拒後，資料庫（含 CE 表、代理表、工作表）位元組與被拒前完全相同，沒有留下半個 CE | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-20 | R4；`update` 沿用建立的規則 | 例外 | 已有帶三鍵（TC-NK-01 的值）的 CE `lab-a`，已記下 `ce show lab-a` 的輸出 | 對 `lab-a` 更新，分別把 modules 改成 `["a;b"]`、把 `sitePipelines[0].home` 改成 `$(id)` | 兩次都被拒，原因點名鍵名；再查看 `lab-a`，輸出與更新前一模一樣（含最後更新時間） | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-21 | R4；專長守則（錯誤訊息說原因與處理方式、不露堆疊與內部路徑） | 例外 | 空的平台 | 做 TC-NK-06、TC-NK-10、TC-NK-11、TC-NK-14 各一個被拒的建立，收集畫面輸出 | 每則訊息都說出「哪個鍵、哪個值有問題」並說出可以怎麼改（講出允許的字元或形式，例如英文字母、數字與哪些符號；或「必須是 擁有者/名稱」）；輸出裡沒有 `Traceback`、沒有程式檔路徑、沒有 SQL | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-22 | R6；專長守則（密鑰不得出現在回應與資料庫） | 例外 | 空的平台。下面的假憑證含有字樣 `CANARY` 方便搜尋 | 建立 CE，`modules=["abf_CANARYsecret9f2c71aa0123456789abcdefghij"]`（長得像平台自己的 token，但字元合乎 module 規則） | 被拒，原因說明「長得像憑證，平台只記名字，憑證要放代理那邊」（與既有 TC-036 的說法同類）；畫面輸出與資料庫位元組裡都找不到 `CANARY` | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-23 | R6 | 例外 | 空的平台 | 建立 CE，`siteConfigVars=["<AKIA 接 CANARYZZ99887766，共 20 字，寫成一串>"]`（長得像 AWS 金鑰編號，卻合乎環境變數名規則） | 被拒，原因是長得像憑證；畫面輸出與資料庫位元組裡都找不到 `CANARY` | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-24 | R6（計畫原話：避免有人把 token 塞在 `home`） | 例外 | 空的平台 | 建立 CE，`sitePipelines[0].home="<AKIA 接 CANARYZZ99887766，共 20 字，寫成一串>"`，其他欄位合法 | 被拒，原因是長得像憑證；畫面輸出與資料庫位元組裡都找不到 `CANARY` | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-25 | R4；「鍵名已定案，不要改鍵名」 | 例外 | 空的平台 | 建立 CE，設定裡拼錯鍵名：`sitePipeline`（少一個 s）、`siteConfigVar`、`module` | 每一次都被拒，原因說這是未知的設定並點出壞鍵名（現有「unknown setting」行為），且已知設定清單裡含正確的 `modules`、`siteConfigVars`、`sitePipelines` | 自動：`platform/tests/test_station_envs.py` |

## User Story 3 — 既有的東西完全不變，也不需要 migration（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-NK-26 | R7、R5 | 功能 | 空的平台 | 建立一個完全不帶三鍵的 slurm-platform CE（例如沿用既有 `test_tc024` 那組參數），再查看 | 建立成功；查看到的 config 裡沒有 `modules`、`siteConfigVars`、`sitePipelines` 任何一個鍵（沒有憑空補空清單），其餘內容與此改動前的行為相同 | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-27 | R7、R8 | 功能 | 已有一個沒帶三鍵的 CE `lab-a`（等於改動前建的舊資料） | 更新 `lab-a` 的 `--work-dir`，再查看 | 更新成功；工作資料夾變了；config 仍然沒有三鍵；`ce list`、MCP 的 `list_compute_envs` 仍然正常列出它 | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-28 | R8；專長守則（結構有變動要附 migration 或寫明理由） | 功能 | 全新的平台資料庫 | 建立一個含三鍵的 CE，之後列出資料庫 `compute_envs` 表的欄位 | 欄位清單與此改動前完全一樣（id、name、description、platform、credentials_id、agent、status、message、is_primary、checked_ok、config_json、created_at、updated_at、last_used_at、owner_user_id）；三鍵只出現在 `config_json` 這一欄的 JSON 內；沒有新欄位、新表 | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-29 | R8 | 功能 | 實作完成後的 `specs/ce-nano4-keys/ledger.md` | 驗收者讀 ledger | ledger 寫明：已核對 CE 是以 JSON 欄位（`config_json`）整份儲存、所以不需要 migration，並指出核對的依據（例如 `store.py` 的表定義）；沒有改走 BLOCKED | 手動：驗收者直接讀 ledger；`docs/TESTING.md` 無對應步驟，見總覽疑問 |
| TC-NK-30 | R9 | 功能 | 實作完成 | 跑 `platform/tests/test_station_envs.py` 內既有的 `test_tc024_…`、`test_tc029_…`（兩支）、`test_tc036_…`、`test_tc038_…` 等原有測試 | 全部通過 | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-31 | R9 | 功能 | 與 base 分支（v3）比對 | 驗收者看 `git diff v3...HEAD -- platform/tests/test_station_envs.py` | 差異只有「新增」的測試；既有 `test_tc024`、`test_tc029` 系列的程式碼與斷言沒被刪、沒被放寬、沒被改預期值、沒被加 skip | 手動：驗收者直接比對 diff；`docs/TESTING.md` 無對應步驟，見總覽疑問 |
| TC-NK-32 | R10（全套測試綠） | 功能 | 在 WSL 或 Linux 的本機磁碟上 | 跑 `tests/run_all.sh`（Git Bash 下用 `wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree> && bash tests/run_all.sh'`） | 全部通過，且執行者完成記號 `GREEN <HEAD sha>` 與 HEAD 相符 | 自動：`tests/run_all.sh` |
| TC-NK-33 | R10（完成標準：真的用 CLI 存得進去） | 功能 | 一個真的 `abf-platform` 行程（不是函式內呼叫），資料位置指到暫存資料夾 | 在命令列執行 `abf-platform ce create --name lab-n --platform slurm-platform --work-dir=/data/work --head-queue=normal --config-json '<TC-NK-01 的三鍵>'`，再執行 `abf-platform ce show lab-n` | 兩個指令結束碼都是 0；`show` 印出的 JSON 裡 config 含三鍵且內容與送入一致；同樣的指令改成 `modules=["a;b"]` 則結束碼非 0、印出拒絕原因含 `modules`、資料庫沒新增列 | 自動：`platform/tests/test_station_envs.py` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-NK-34 | R11（不改站台） | 不在範圍 | 與 base 分支（v3）比對 | 驗收者執行 `git diff v3...HEAD --stat` | 變動的檔案只有計畫範圍內的 `platform/abf_platform/compute_envs.py`、`platform/tests/test_station_envs.py`，加上 `specs/ce-nano4-keys/` 底下的文件（ledger 等）；`platform/abf_station/` 底下一個檔案都沒動 | 手動：驗收者直接 `git diff`；見總覽疑問 |
| TC-NK-35 | R11（不碰 SU） | 不在範圍 | 同上 | 看同一份 diff | `su.py`（含 `platform/abf_platform/` 與 `platform/abf_station/` 底下任何叫 `su.py` 的檔）沒有任何變動；`compute_envs.py` 的改動裡沒有出現費率、SU、點數的處理 | 手動：驗收者直接 `git diff` |
| TC-NK-36 | R11（不建 nano4 的實際 CE JSON） | 不在範圍 | 同上 | 看同一份 diff 新增的檔案清單 | 沒有新增任何 nano4 的 CE 設定檔（沒有含 `nano4`、`biology/Nextflow/26.10.0` 這類實際站台值的設定 JSON 或範例檔）；測試裡用的值只存在於測試程式裡 | 手動：驗收者直接 `git diff` |
| TC-NK-37 | R12（不加 preRunScript／postRunScript 的新處理） | 不在範圍 | 同上 | 看 `compute_envs.py` 的 diff | 這兩個鍵的既有處理（`_COMMON_CONFIG` 清單、`_text` 的長度檢查）一字未改；新增的只有三鍵與它們的檢查；沒有把 module／sitePipelines 變成「可帶腳本」的入口 | 手動：驗收者直接 `git diff` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-NK-38 | 第 3、4 條（沒有寫死的個人／叢集路徑；指令層不點名排程器） | 功能 | 實作完成 | 跑 `bash tests/no_hardcoded_paths.sh` 與 `bash tests/command_layer_is_site_neutral.sh` | 兩支都通過；新程式碼與測試裡沒有 `/home/<人>/`、`/work/<人>/` 之類的路徑 | 自動：`tests/no_hardcoded_paths.sh`、`tests/command_layer_is_site_neutral.sh` |
| TC-NK-39 | 專長守則：對等性（動作清單＝動作層函式清單） | 功能 | 實作完成 | 跑既有的 `platform/tests/test_actions_layer.py`、`platform/tests/test_web_parity.py`，以及 `test_station_envs.py` 內的 `test_tc063_…`、`test_tc071_…`、`test_tc084_…` | 全部通過且這些測試沒被改過（比對 diff）：這次沒有新增任何命令列子指令、HTTP 路徑或 MCP 工具，動作清單與動作層函式清單兩邊仍一一對應 | 自動：上述測試檔 |
| TC-NK-40 | 專長守則：跨使用者讀取 | 例外 | 兩位使用者 A、B；A 名下有一個含三鍵的 CE（TC-NK-01 的值） | 用 B 的身分透過動作層（`get_compute_env`、`list_compute_envs`）去讀 A 的這個 CE | B 讀不到：`get_compute_env` 的結果與「查無此 CE」相同，`list_compute_envs` 裡沒有它；三鍵內容不出現在 B 看到的任何回應裡；A 自己讀得到 | 自動：`platform/tests/test_station_envs.py` 或 `platform/tests/test_owner_binding.py` |
| TC-NK-41 | 專長守則：跨使用者修改；確認管道（沒有未經確認的寫入路徑） | 例外 | 兩位使用者 A、B 各有個人存取 token；A 名下有含三鍵的 CE，已記下資料庫位元組 | 用 B 的 token 對 `/ce`、`/compute-envs`、`/jobs` 等路徑送 POST／PUT／PATCH／DELETE，內容是要改 A 的 CE 的三鍵 | 每個請求都被拒或不存在（401／404／405）；資料庫位元組完全沒變。也就是說，改 CE 設定只有本機終端機的 `ce` 指令這一條路，網頁與 MCP 都沒有 | 自動：`platform/tests/test_station_envs.py` |
| TC-NK-42 | 專長守則：確認管道（唯讀工具不寫入）、密鑰不外洩 | 功能 | 有一個含三鍵的 CE，已記下資料庫所有檔案的摘要 | 用 MCP 的 `list_compute_envs`、`get_compute_env` 讀它 | 讀完後資料庫檔案摘要與讀之前相同（沒有寫入）；回應裡沒有任何 token 或 Authorization 字樣 | 自動：`platform/tests/test_station_envs.py` |
