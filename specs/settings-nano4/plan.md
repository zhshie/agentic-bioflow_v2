---
id: settings-nano4
title: 文件：nano4 的設定鍵、站台對照表一列、兩條踩坑
tier: A
kinds: docs
lane: L3
base: v3
---

# settings-nano4（M1-06）

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/settings-nano4/plan.md`。**只處理本任務**。L1／L2 的程式同時在開發，**鍵名以本檔為準**（與它們的計畫一字不差）。

## 目標
使用者（或同事）照 `docs/SETTINGS.md` 就能把站台代理設成 nano4 模式；維護者照 `docs/SITE_ADAPTER.md` 看得出 nano4 與 Taiwania-3 在六個契約上的差別。

## 維護者原話（verifier 出題用）
- 「文件與驗收表：設定鍵、站台對照表、踩坑紀錄、實機驗收清單。」（白話摘要第 3 點）
- 「不另加任務，只在 M1-06 的 SETTINGS／OPERATIONS 補『公開網址』一節。」（裁示 11）
- 「試用成功＝同事不問我就能跑完一次 16S。」（裁示 17）——文件要讓同事照做。

## 範圍：檔案
- `docs/SETTINGS.md`
- `docs/SITE_ADAPTER.md`
- `docs/PITFALLS.md`
- `docs/OPERATIONS.md`（只加「公開網址」一節）

## 作法
- `SETTINGS.md` 加三個站台 settings 鍵，各一行用途、型別、預設、例子：
  - `way_back`: `forward | direct`，預設 reach 為 ssh 時 `forward`；`direct` 需要 `platform_public_url`。
  - `platform_public_url`: https 網址（loopback 例外，只給測試）。
  - `site_profile`: `taiwania3 | nano4`（給文件與預設值分流；程式目前不讀，標「保留」）。
  - 以及 CE 的三個鍵 `modules`、`siteConfigVars`、`sitePipelines`（指向 `configs/sites/nchc-nano4-ce.json` 當範例；該檔由 L2 產生，文件先寫路徑）。
- `SITE_ADAPTER.md` 六契約表加 nano4 一列：Resource＝國網 `$NFCORE_SITE_CONFIG`／`selectQueue`，退路 `configs/sites/nchc-nano4.config`；Egress＝計算節點直連外網、無 relay；Reports＝`-with-tower` 直達 `platform_public_url`；Storage＝`/work/u9613010`；Reach＝ssh，2FA 由使用者開 ControlMaster；Identity＝同 T3。
- `PITFALLS.md` 加兩條（照該檔既有編號與格式）：「國網映像快取唯讀→用 `NXF_SINGULARITY_LIBRARYDIR` 查、`NXF_SINGULARITY_CACHEDIR` 另指可寫目錄」、「本地 pipeline 路徑不可帶 `-r`」。
- `OPERATIONS.md` 加「公開網址（進度回報）」一節：為什麼需要 https、Tailscale Funnel 是其中一種做法（步驟指向維護者自己的筆記，不在此展開）、`way_back: direct` 時站台怎麼驗（`curl https://<public>/user-info` 應回 401 並帶 `X-ABF-Platform`）。

## 失敗先行測試
文件任務的「測試」＝可機械檢查的一致性：
- 新增 `tests/docs_nano4_keys.sh`（或併入既有 docs 測試，由 executor 依 `tests/` 慣例決定並在 ledger 說明）：grep `docs/SETTINGS.md` 必含 `way_back`、`platform_public_url`、`site_profile`、`modules`、`siteConfigVars`、`sitePipelines`；`docs/SITE_ADAPTER.md` 必含 `nano4` 列與 `NXF_SINGULARITY_LIBRARYDIR`；`docs/PITFALLS.md` 兩條標題存在。先寫、現在會紅。

## 完成標準
三份文件鍵名與 L1／L2 計畫一字不差；新測試綠；全套綠。

## 環境事實
- nano4 探測摘要見 `ce-nano4-keys` 計畫的「環境事實」；本任務不連真機。

## 不做
- 不改 `README.md`、ADR、ROADMAP（M1-08，C 級，維護者合併）；不改 `docs/TESTING.md`（M1-07）。

## 專長守則（docs）

（工作區沒有 `.claude/dev-profiles/docs.md`；本任務無專長守則。）
