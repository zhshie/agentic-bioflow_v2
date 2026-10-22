---
id: acceptance-nano4
title: nano4 實機驗收：TESTING.md 加 TC-047n～051n、驗收表
tier: A
kinds: docs
lane: L3
base: v3
---

# acceptance-nano4（M1-07）

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/acceptance-nano4/plan.md`。**只處理本任務**。前置：同車道 `settings-nano4` 已完成。

## 目標
維護者週三／四在 nano4 親自跑一次 16S 時，有一張照著填就能證明「端到端通了」的驗收表；之後同事試用也用同一張。

## 維護者原話（verifier 出題用）
- 「第一里程碑＝16S（nf-core/ampliseq 2.18.0）在 nano4 端到端：Claude Desktop 或網頁 → 不經 Seqera → 啟動 → 結果頁。」（裁示 7）
- 「每次先估 SU、記帳。」（裁示 3）
- 「nano4 若週四跑不通 → 先在 `/work/u9613010` 自裝 Nextflow＋插件跑通」（裁示 17）——驗收表要有「走哪條路」欄。

## 範圍：檔案
- `docs/TESTING.md`
- `specs/007b-launch/acceptance-nano4.md`（新）

## 作法
- `TESTING.md` 手動案例加：
  - TC-047n：nano4 preflight 全項通過（列出每一項名稱）。
  - TC-048n：從 Claude Desktop `launch nf-core/ampliseq 2.18.0` → `/c/<rid>` 本人確認 → `squeue` 看到 head 在 `ngsconsole`、子作業在 ngs 分區。
  - TC-049n：從計算節點 `curl https://<public>/user-info` 回 401 且帶 `X-ABF-Platform`，relay 未啟動（取代 T3 的 relay 檢查）。
  - TC-050n：平台收到 trace、結果頁可見。
  - TC-051n：模組缺席時退回 `owner/name -r rev`（用一個不在 `sitePipelines` 的 revision）。
- `acceptance-nano4.md` 驗收表欄位：日期、走哪條路（國網模組／自裝 Nextflow）、preflight 每項結果、`head.sh` 全文（貼上）、`squeue` 輸出、trace 行數、`grep -c token` 必須為 0、`wallet` 前後 SU 與差額、結果頁截圖檔名、備註。
- 每條手動 TC 都寫到「非工程師照著做」的粒度（指令完整、預期輸出寫出來）。

## 失敗先行測試
- 新增／擴充 docs 檢查：`docs/TESTING.md` 必含 `TC-047n`～`TC-051n` 五個 ID；`specs/007b-launch/acceptance-nano4.md` 存在且含 `wallet`、`squeue`、`X-ABF-Platform`。先寫、現在會紅。

## 完成標準
五條 TC 與驗收表存在、文字可照做；docs 測試綠；全套綠。真機填表是維護者的事，不在本任務。

## 環境事實
- nano4：帳號 `mst109178`、head 分區 `ngsconsole`、子作業 ngs 分區、Slurm 25.11.4（`memory/reference/nchc-nano4-probe-2026-10-20.md`）。
- `wallet` 是國網查 SU 餘額的指令（探測筆記）。

## 不做
- 不跑真機、不改程式。

## 專長守則（docs）

（工作區沒有 `.claude/dev-profiles/docs.md`；本任務無專長守則。）

## 裁決（2026-10-22，developer-agent，回應 verifier 出題退回）
1. **launch 前先估 SU**：驗收表加欄「launch 前預估 SU」（用 `estimate_su`／`abf-platform` 的估算，寫指令與輸出），與「wallet 前後差額」並列；TC-048n 第一步就是估算。採 verifier 的 TC-B15。
2. **`grep -c token` 的對象**：run 資料夾裡的 `head.sh` 與 Slurm 輸出（`slurm-<jobid>.out`）各做一次，兩者都要 0；`tower.token` 檔本身不在掃描範圍（它就是放 token 的地方）。指令完整寫進表格。
3. **檔案範圍補 `tests/docs_nano4_acceptance.sh`**（新檔，docs 檢查：TESTING.md 有「nano4 acceptance」一節、acceptance-nano4.md 的表有必要欄位），run_all 自動收進去。
4. **前置**：本任務不等 settings-nano4／程式合併；文件照計畫與 ce-nano4-keys、launch-site-pipeline、way-back-direct 三份計畫的字面寫，程式行為由實機驗收時對照。驗收表頂部註明「依 2026-10-22 計畫撰寫；實機跑時以當時 v3 為準」。
5. **preflight 項目清單**：以 docs/PLATFORM.md 的 Preflight 表（8 項）為準，另加 preflight-nano4 合併後的 3 項（modules／site_pipeline／library），表中標「（preflight-nano4 合併後）」。
6. **首次驗收只走 Claude Desktop**（裁示 7 的「或網頁」留給 M2 網頁全流程時再驗）；表中留一列「網頁路徑：M2」。
7. **指令細節**：「relay 未啟動」用 `abf-platform launches` 顯示 `way_back: direct` 且站台 `ss -ltnp | grep -c <relay port>` 為 0；「從計算節點 curl」用 `srun -p ngstest -A mst109178 -N1 -c1 -t 00:05:00 curl -sS -o /dev/null -w '%{http_code}' <public_url>/health`（探測筆記用 ngstest）；trace 行數數 run 資料夾的 `trace.txt`（扣表頭）。
