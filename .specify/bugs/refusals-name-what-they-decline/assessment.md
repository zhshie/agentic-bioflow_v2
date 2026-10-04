# Bug Assessment: some refusals do not say whether they decline a shell, a folder or a capability; one says opposite things about a synced folder

- **Slug**: refusals-name-what-they-decline
- **Created**: 2026-10-05
- **Source**: constitution 2.0.0 invariant 11 audit (low); SN4 consistency
- **Verdict**: valid
- **Severity**: low (wording only; no behaviour changes)

## 給維護者

1. 憲法第 11 條要求每一個拒絕都要講清楚「拒絕的是你的 shell、你的資料夾、還是少了一個能力」。`on_site.sh` 的 WSL 拒絕已經寫了；但設定檔權限拒絕、`--use` 的三個拒絕、缺 jq、Git Bash 找不到 WSL 這幾條沒寫。
2. 補上同一個句型：`What is refused is ...`，並由測試檢查。
3. 另一處前後矛盾：權限拒絕說雲端硬碟資料夾「不適合放 token」，同步資料夾提醒卻說它是 token 的「intended home」。照比較安全的讀法統一：同步資料夾可以放根目錄，但放 token 並不理想。

## Where

- `scripts/settings.sh`: `refuse_unwritable_mode`, the three refusals in `use_root`, `cloud_sync_caution`
- `scripts/detect_conditions.sh`: the `blocked-no-jq` and `unsupported-msys-no-wsl` messages

## Remediation

Add one sentence per refusal naming what is refused (checked in `tests/settings_test.sh`, `tests/conditions_matrix_test.sh`); change "That is the intended home for it" to say a synced folder is accepted for the root but is a poor place for the token.
