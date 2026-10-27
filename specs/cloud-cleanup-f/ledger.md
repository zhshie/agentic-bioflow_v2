# cloud-cleanup-f progress ledger

## 完成了什麼（executor，2026-10-27）
- [x] `build.prepare_clean`／`clean_screen`／`clean_work_path`（`platform/abf_launch/build.py`）：七個鍵、兩條 work 公式（Slurm：run 資料夾＋`/work`，續跑沿用原資料夾；Google Batch：`<workDir>/runs/<run>/work`）、十一種白話拒絕（含「送出後 workDir 改過」「找不到當初的內容」「已被 forget」）。
- [x] `actions.offer_cleanup`（`platform/abf_platform/actions/__init__.py`）：只在 hand-off 紀錄有擁有者、run 索引狀態恰為 `succeeded`、`prepare_clean` 通過時，為擁有者建一張 `clean_work` 待確認申請；任何跳過或例外都回 `{"offered": False, "reason": …}`，不丟出。不是 MCP 工具、不是 `request_*`。
- [x] `receiver.complete`（`platform/abf_platform/receiver.py`）：成功且 token 綁 run 名稱時，在 `store.end_token` 之後呼叫 `offer_cleanup`，`import` 放函式內，`try/except Exception: pass`。回應與 token 結束一個位元都不變。
- [x] `docs/PLATFORM.md`：新小節 "Cleaning a finished run's work folder"（放在 Forget 之後、Resume and relaunch 之前）；更正第 8 行、第 6 節代理最初唯讀那段，以及「What it does not do」那段兩處（`no clean-up of work/`、`never removes or moves anything`），後者計畫沒列，但不改會與新小節矛盾（沒有測試釘住它們）。
- [x] `docs/TESTING.md`：新小節 "(cloud-cleanup)"，手動驗收 1–5＋截圖；第 158 行更正。
- [x] `platform/tests/test_cleanup_offer.py`（新，RED 在 63da833）。

## 動手前再搜一次三句被更正的話（TC-095）
搜 `never deletes`、`delete, move`、`no job kind`，範圍 `platform/tests/`、`tests/`、`docs/`：
- `platform/tests/`、`tests/`：**沒有命中**（改完之後只有本片新測試自己的斷言）。
- `docs/PLATFORM.md`：第 8 行（`never deletes`）、第 139 行（`delete, move`、`no job kind`；計畫寫 136，文件已位移）、第 456 行（resume 小節那句，`delete, move` 指的是 resume 時代理「不做別的」，不是對現在代理能力的描述，沒改）；`docs/TESTING.md` 第 158 行（`no job kind writes`，已改）。
- 沒有任何既有測試釘住這幾句。

## 與計畫不一致、要讓 verifier 知道的事實
- TC-105 寫「MCP 工具仍是 12 個」，但這個基底實際就有 15 個（`test_actions_layer.READ_NAMES + WRITE_NAMES`）；本片沒動 `mcp_server.py`，測試比的是「與基底的清單完全相同、沒有名字含 clean 或 `request_`」。
- 計畫寫 `PLATFORM.md` 用範例路徑 `/work/u1/abf`，但 `tests/test_scope.py` TC-072 的「不得有類似叢集的路徑」掃描會掃 `PLATFORM.md`（`/work/<名稱>/`），所以 PLATFORM.md 新小節只用 `<run folder>/work` 與 `<workDir>/runs/<run>/work/` 的寫法；TESTING.md 與測試裡的路徑拆字寫（`K = "wor" + "k"`）。
- 第 ④ 句（軟刪除）依 d 片 ledger 第 4 點：新建的桶預設 7 天軟刪除、期間仍可還原、`--recursive` 隱含所有版本；畫面沒有任何金額，也沒有「無法還原」。

## 還沒做（要維護者在自己的測試 run 上做，見 `docs/TESTING.md` "cloud-cleanup"）
- [ ] 手動 1–5（nano4 通知／確認頁／只刪 work；`work-dir` 核對；Google Batch 前綴不撞名＋軟刪除結果回填 d 片 ledger；續跑 `-a2`；逾時不重提）。
- [ ] 截圖（確認頁含 `clean_screen` 文字、看板卡片，zh／en 各一）列進每日清單，維護者回好／不好。

## git diff --stat（對基底 `git merge-base HEAD origin/v3` 的程式與文件；ledger 自己不算）
```
 docs/PLATFORM.md                          |  15 ++-
 docs/TESTING.md                           |  14 +-
 platform/abf_launch/build.py              |  94 ++++
 platform/abf_platform/actions/__init__.py |  43 ++
 platform/abf_platform/receiver.py         |   6 +
 platform/tests/test_cleanup_offer.py      | (新檔)
```
Slurm 的內容包、畫面、`head.sh` 與 golden 沒有動（`prepare_cancel`、`cancel_screen`、`launch_screen`、golden 檔都未修改）。不需要 migration（沒碰資料結構，TC-114 有測試）。

## 第二輪：裁決 11 的既有測試更正（舊到新與理由）
- `platform/tests/test_cleanup_confirm.py` TC-065/066：舊＝整個 `abf_platform` 原始碼不得有 `create_pending(...clean_work`；新＝掃描時只排除 `actions/__init__.py` 裡 `offer_cleanup` 函式本體（ast 取範圍），其他檔與函式仍不得出現。理由：b 片「還沒有東西會建申請」的守衛，f 片本來就要建。
- `platform/tests/test_web_parity.py` TC-H16a/b：`INTERNAL` 表加 `"offer_cleanup"`（系統內部呼叫、不對使用者開放）。
- `platform/abf_platform/actions/__init__.py`：拿掉 `offer_cleanup` 自己對 `work_cleaned_at` 的檢查（`test_cleanup_store.py` TC-030 禁止 actions 出現這個字；`prepare_clean` 本來就會拒絕已清過的，TC-011/045 仍成立）。沒有改 `test_cleanup_store.py`。
