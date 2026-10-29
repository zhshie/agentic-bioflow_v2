# Kubernetes 計算環境 progress ledger

## 進度

- [x] `compute_envs.py`：`K8S` 常數、`CHECK_ONLY_TYPES=(K8S,)`、`_check_k8s`、`clean()` 分支、`snapshot()` 的 K8s 分支（9 個鍵）。
- [x] 新檔 `abf_station/k8s_preflight.py`（七項唯讀預檢，經 `site.run_fixed`）。
- [x] `handlers.py` 接線；`jobs._target` 的 CHECK_ONLY 拒絕句改成 Kubernetes／k8s-launch；`cli.py` 五個旗標。
- [x] 新測試檔 `platform/tests/test_k8s_ce.py`（RED 提交 98c7d80，其後逐步轉綠）。
- [x] 文件：`docs/PLATFORM.md`（K8s 小節、型別表、第 8 節句子）、`docs/SEQERA_PARITY.md`、`docs/TESTING.md`。

## 既有測試的有意更新（計畫表 A／B／C 與裁決 12）

| 表 | 檔案:行 | 改前 | 改後 |
|---|---|---|---|
| A | test_azure_ce.py:721-722 | `CHECK_ONLY_TYPES == ()`；`CHECKABLE` 四項 | `== ("k8s-platform",)`；`CHECKABLE` 末尾加 `"k8s-platform"` |
| A | test_azure_launch.py:983-984 | 同上 | 同上 |
| A | test_aws_launch.py:985-986 | 同上 | 同上 |
| A | test_aws_ce.py:907-908 | 同上 | 同上 |
| A | test_gcb_ce.py:853-854 | 同上 | 同上 |
| B | test_station_envs.py:18,23 | `# the 10 types`；`UNSUPPORTED` 含 `k8s-platform` | `# the 9 types`；刪掉該項（參數化從 10 變 9） |
| B | test_station_envs.py:161 (tc032) | 集合四項 | 加 `"k8s-platform"`（`len(KINDS)==14` 不動） |
| B | test_aws_ce.py:788；test_azure_ce.py:901；test_gcb_ce.py:816 | `len(UNSUPPORTED) == 10` | `== 9` |
| B | test_azure_ce.py:902 | 迴圈含 `"k8s-platform"` | 拿掉它 |
| B | test_station_docs.py:78,82 (tc077) | 略過四型；總數 10 | 略過加 `"k8s-platform"`；總數 9 |
| C | test_aws_ce.py:924；test_azure_ce.py:863；test_azure_launch.py:1213；test_azure_upload.py:855；test_gcb_ce.py:867；test_gcb_launch.py:1151 | `...can run; the other ten types can be modelled only` | 換成含 Kubernetes 的新句子（`the other nine`）；azure_ce 仍保留 `"the other eleven" not in d`；azure_launch 仍 `count >= 2` |

沒有刪除、略過或放寬任何斷言。test_azure_upload.py 不在計畫檔案清單內，依裁決 12 納入。

## 實作前全套測試（計畫 D 表末條）

在 `599e5eb`（合約提交、尚無任何實作）的獨立 worktree 跑 `abf-fast-suite <worktree> --retry-failed-once`（2026-10-29，WSL）：**134/134 passed，all green，沒有任何紅，沒有重跑**。D 表沒列到的紅：無。已知環境紅 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 在這次跑沒有出現（未紅），所以不需要「視為綠」的例外。（第一次嘗試的跑被中途終止，結果作廢，上面是重跑的完整結果。）

## D 表（確認不變）

`test_tc085`、`test_launch_cli` 的 test_tc063、`test_station_static` 掃描、TC-060 說明文字掃描、MCP 工具數（15）、test_scope tc070、test_aws_clean／aws_upload／azure_launch 的 `CLOUD_JOB_KINDS` 斷言：都未修改；相關檔已在本分支跑過全綠（見全套測試）。

## TC-045：kubeconfig 缺口（只記錄，沒有加規則）

用 `credential_findings` 探測：`client-certificate-data: <base64>`、`client-key-data: <base64>`、`certificate-authority-data: <base64>` 這三種開頭的行貼進 `description`，現有規則**都沒有擋下**（回傳 `[]`）。只有 `token: …` 這類會被 `token\w*\s*[=:]\s*\S` 擋住。依裁決 6，本片不新增規則；請 developer-agent 決定是否另開任務。

## 未驗證的四件事（見 docs/TESTING.md「Kubernetes environment (k8s-ce)」）

離線的 `config get-contexts`、`accessModes` 輸出是否以空白分隔、`KUBECACHEDIR` 的實際效果、最小權限 RBAC：自動測試只用假 runner，真叢集步驟留給維護者（TC-166）。

## 其他備註

- TC-036 的「含 KTOK 的字串」（修正輪）：第三個壞名字改成 `"to"+"ken: "+KTOK`（把 KTOK 寫成 token 指派，就是從 kubeconfig 貼上的樣子），並多斷言拒絕訊息不含 KTOK；原本的 `"k8s="+KTOK` 已拿掉。**仍未滿足的部分**：純 KTOK（只有英數、53 字）形狀上是合法憑證名字，`_CRED_NAME` 與 `credential_findings` 都不會拒；要拒就得新增「長得像 token 的名字」規則，但計畫裁決 6 說這片不加規則。TC-036 原文可能寫太滿，請 developer-agent 決定改合約或加規則，這片不自行決定。
- 提交的 Co-Authored-By 行採用本場 system 提示給的 Sonnet 5.5 版本，與派工單寫的 Opus 5.5 不同。
