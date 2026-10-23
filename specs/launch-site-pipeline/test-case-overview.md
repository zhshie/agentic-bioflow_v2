# 測試案例總覽：站台啟動先 module load，命中 sitePipelines 用本地路徑啟動（launch-site-pipeline，M1-02）

狀態：合約已確認（2026-10-23，verifier）

**規格**：`specs/launch-site-pipeline/plan.md`（本任務無 spec.md，含裁決 0–12）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 命中 sitePipelines：先 module load，用本地路徑啟動 | 13 | 0 | 0 | 13 |
| US2 — 未命中照舊從遠端拉；module 載入失敗就停下 | 7 | 2 | 0 | 9 |
| US3 — 計算環境三鍵帶進站台並在站台再驗 | 5 | 8 | 0 | 13 |
| US4 — 續跑也從本地路徑、也先 module load | 7 | 0 | 0 | 7 |
| US5 — 代理重建一致、來源紀錄寫進 bundle | 4 | 2 | 0 | 6 |
| 憲法與安全網（含專長守則 backend） | 3 | 4 | 0 | 7 |
| 不在範圍 | 0 | 0 | 6 | 6 |
| **合計** | 39 | 16 | 6 | 61 |

自動驗證 59 條、手動驗證 2 條（手動：TC-LS-48 讀 ledger；TC-LS-59、TC-LS-60 另需驗收者讀 diff，兩條同時有自動部分）。其中 TC-LS-48 純手動，TC-LS-59、TC-LS-60 為「手動＋自動」，計入手動 2 條時只算 TC-LS-48 與 TC-LS-59 的 diff 步驟；精確分法：純手動 1 條（TC-LS-48）、手動加自動 2 條（TC-LS-59、TC-LS-60）、其餘 58 條純自動。

## 請你判斷的三件事

1. **每條是不是你要的？** 重點看 TC-LS-04（命中時最後一行的完整樣子）、TC-LS-14（沒命中時的樣子）、TC-LS-21／22（module 載入失敗就整份腳本停下，不退回遠端）。
2. **有沒有漏掉的出錯情況？** 想像實驗室成員會怎麼用錯它：CE 填了 `a;b` 之類的模組名、變數名寫成小寫、同一個 pipeline 登記兩次，這些都已列在 TC-LS-10、28–32。
3. **「不在範圍」對嗎？** 這次不做：`-profile singularity`、`nfcore-submit`、queue、`_tower`／`own_facts`／preflight、CE 驗證規則本身、失敗自動退回遠端（TC-LS-56 至 61）。

## 覆蓋檢查

- plan 的需求共 12 條（作法 8 條要點、失敗先行測試 3 條、完成標準 1 條）＋裁決 0–12 的可檢查項，全部都有測試案例：是
  - 失敗先行測試三條：`test_tc013b_a_…`→TC-LS-01；`test_tc013c_a_…`→TC-LS-14；突變 `modules=["a;b"]`→TC-LS-28。
  - 完成標準（兩行 module load、exec 行、未命中逐位元不變、全套綠）→TC-LS-02、04、16、17。
  - 裁決 0→TC-LS-23、24、26、27、60；裁決 1→TC-LS-01、23、27；裁決 2→TC-LS-04、08、09；裁決 3→TC-LS-14、15、16、20；裁決 4→TC-LS-47、48；裁決 5→TC-LS-36 至 38、41；裁決 6→TC-LS-39、48；裁決 8→TC-LS-29 至 32；裁決 9→前言（假 CE 一律用裁決 1 的值）；裁決 10→TC-LS-03、10、21、22、40、42；裁決 11→TC-LS-56；裁決 12→TC-LS-21、22、61。
  - 裁決 7 已被裁決 11 刪除，不出題（以 TC-LS-56 反向確認）。
- 維護者原話共 2 條，全部有用他原話當輸入與預期結果的測試案例：是
  - 原話 1（`nextflow run $NFCORE_<P>_HOME … -c $NFCORE_SITE_CONFIG -c $NFCORE_SITE_REFERENCES`、不走 `nfcore-submit`、缺 module 退回 `owner/name -r rev`）→ TC-LS-06、13、19、57。
  - 原話 2（對外介面不變：`nf-core/ampliseq` ＋ `2.18.0`）→ TC-LS-12、52。
- 計畫的驗收情境（命中／未命中／突變）共 3 條，全部都有測試案例：是
- 計畫「不做」共 3 條（不改 `_tower`／`own_facts`、不改 preflight、不改 `compute_envs.py`——後者已被裁決 0 改成只改 `snapshot`）＋裁決 11、12 共 5 條，全部都有「不在範圍」測試案例：是（TC-LS-56 至 61）
- 專長守則（backend）：對等性→TC-LS-52；跨使用者讀／寫→TC-LS-50、51；確認管道→TC-LS-49；錯誤訊息與日誌→TC-LS-35、53；migration→TC-LS-47、48（本任務不改資料表，改以「欄位不變」加「ledger 明寫不需要」證明）。專長守則的 executor 規則 1（動作層一個動作一個函式）與 2（人工確認）由 TC-LS-52、49 覆蓋；規則 3（擁有者過濾）由 TC-LS-50、51 覆蓋。

## 我（撰寫者）不確定的地方

- 無會改變「檢查什麼」的疑問。以下是給 developer-agent／維護者的備註，不影響合約成立：
  1. **`-profile singularity`**：維護者原話的手動啟動行有 `-profile singularity`，裁決 11 決定平台的 `exec` 行不加，改由站台 config（`nano4-site-config` 任務）提供 singularity。TC-LS-56 依裁決 11 出題（兩種情況都沒有 `-profile`）。這個決定的風險在別的任務：若站台 config 沒開 singularity，命中時會用不到容器——請在驗收時用 `nextflow config` 列印確認，不在本任務測。
  2. **module 行的確切位置**：計畫只說「`umask 077` 之後」，TC-LS-03 只檢查在 `umask 077` 之後、`exec` 之前、Nextflow 先於 ampliseq，不限定與 `cd`、`export` 行的先後。
  3. **若命中項的 module 已經在 `modules` 清單裡**（現有 `test_station_envs.py` 的 NANO4 常數就是這樣）會不會載兩次，計畫沒說；裁決 9 規定本任務的假 CE 不混用，所以不出題。
  4. **測試放哪裡**：範圍檔沒列 `test_resume_render.py`、`test_owner_binding.py`、`test_actions_layer.py`；本合約允許在這些現有檔「只新增案例」（TC-LS-16、17、39、50、51、52），舊案例一字不改。
  5. **真站台上的 `module` 指令**：單元測試用假的 `module` 證明順序與失敗即停；真正的 sbatch 非登入 shell 是否有 `module` 可用，不在單元測試能證明的範圍，留給站台上的驗收。

## 核可紀錄

<!-- 無；由 verifier 確認合約，不是維護者自己核可。 -->
