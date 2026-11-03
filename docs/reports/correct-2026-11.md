# 「犯錯就改系統」掃描報告（correct 2026-11）

範圍：`origin/v3` 最近 400 個 commit、`docs/PITFALLS.md`、測試中註明 regression 的地方。
規則：同一類至少發生兩次才列入。層級：①改架構 ②加檢查 ③行為測試 ④文件。

| # | 類別 | 證據 | 次數 | 建議層級 | 為什麼更高層不行 | 本次 |
|---|---|---|---|---|---|---|
| 1 | 驗證用正規式以 `$` 結尾，放行結尾換行（`"name\n"`） | `98b4fa9`（`releases._REPO`，2026-10-25）；`c727ed4`（七條，2026-10-29，spec `regex-dollar-newline`）；`b23d176`/`86cadfe`（補測試） | 2 次修正輪，共 8 條正規式 | ② 檢查 | ①不可能：Python 的 `$` 語意改不了，也不該包一層自訂 `validate()` 去改寫 22 處呼叫；③行為測試只能一條一條補，下一個照抄舊例的人不會知道要補 | **已實作**：`tests/regex_end_anchor_test.sh` |
| 2 | 測試把「數量／清單／雜湊」寫死，新增工具、job 種類、CE 類型後整批變紅 | `27fb62c`、`35ad72c`、`3e61d87`、`ba753be`、`d8cf65e`、`27dd87e`、`c7b6191`、`3482c59`、`775cf43`、`ebf7a53` | 10+ 個修正輪 | ① 讓測試從單一來源讀清單 | ②檢查很難定義「哪些數字是寫死的」；本次若硬做會誤報大量既有測試，且要動既有測試，超出「只新增檢查」 | 否 |
| 3 | `set -o pipefail` 下 `cmd \| grep -q` 因 Broken pipe 偶發失敗 | `#231`、`6ba3257`（sweep）、`078651c`、`f9f9a72`（修完又在新檔案重犯） | 3 次 | ② 檢查 | 已有 `tests/no_pipefail_grep_q_test.sh` | 否（已有檢查） |
| 4 | 修安全閘時收窄比對範圍，放行舊版會擋的寫法 | CLAUDE.md 校準失敗 #1（#29）、#2（#37） | 2 次 | ③ 行為測試（新舊分支比對） | 涉及 `hooks/`，本次不得修改 | 否 |
| 5 | 測試內的時間／ID 巧合造成偶發紅（如請求 id 含 `fee`） | `fix/clean-page-fee-flake`（#283）、`#231` flake | 2 次 | ③ 行為測試 | 每次成因不同，無共通可掃的寫法 | 否 |
| 6 | 打包／搬移時漏掉產物（圖、run notes） | CLAUDE.md 校準失敗 #3（#39） | 1 次 + 相關 | ③ | 證據不足兩次 | 否 |

## 本次實作：類別 1

`tests/regex_end_anchor_test.sh`（`tests/run_all.sh` 以 `tests/*.sh` 自動收進）：用 `ast` 掃 `platform/`、`scripts/`（不含 tests）中
`re.compile/match/search/fullmatch` 的字面量，開頭 `^`、結尾裸 `$` 者視為驗證用正規式；不在
`tests/regex_end_anchor_baseline.txt` 者即失敗，訊息直接指出改用 `\Z` 或 `re.fullmatch`，並以
`platform/abf_platform/compose.py` 的 `_NAME` 為範例。基線 22 條是現存的未修項目，只能刪不能加；
基線若有已修好卻沒刪的行也會失敗。`REGEX_SCAN_ROOT` 可指向舊 checkout 驗證。

驗證：舊版（`c727ed4^`）失敗並列出 7 條，現在的 v3 通過（指令與輸出見 PR 說明）。

## 後續建議

- 基線 22 條中，`platform/abf_platform/validate.py:14`、`cloud_store.py:11`、`scripts/nf_relay.py:103,220`、
  `scripts/methods_text.py:174-176` 是對外輸入的名稱檢查，應優先改為 `\Z`（改產品行為，需走 Spec Kit bug 流程，本次未動）。
- 類別 2 建議另開 feature：讓釘住清單的測試讀同一份來源。
