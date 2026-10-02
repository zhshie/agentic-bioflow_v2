# Feature Specification: 樣本表的欄位角色不寫死（samplesheet column roles）

**Feature Branch**: `003-samplesheet-roles`

**Created**: 2026-10-02

**Status**: Draft

**Input**: 憲法稽核 C 批（#31）：`scripts/generate_samplesheet.py` 只會把值填進名字剛好叫 `sample`／`fastq_1`／`fastq_2` 的欄位（rnaseq 的慣例）。其他管線把同樣的東西取不同的欄名——ampliseq 叫 `sampleID`／`forwardReads`／`reverseReads`，bacass 叫 `ID`／`R1`／`R2`，mag 叫 `short_reads_1`／`short_reads_2`——結果是整張樣本表空白，只剩一行「每個樣本這欄都是空的」的警告。違反第 6 條（任何管線不需設定）與第 7 條（不需要找維護者）。

> 名詞見 `CONTEXT.md`。本規格給維護者看，用中文；編號照 Spec Kit 慣例。
> 稽核 C 批另兩件：白名單（002，已完成）、新電腦先用公開資料驗證（004，另開）。

## 背景

樣本表（samplesheet）是告訴管線「有哪些樣本、每個樣本的定序檔在哪」的表格。每條 nf-core 管線在自己的 `assets/schema_input.json`（輸入說明檔）裡寫明它要哪些欄。這個說明檔不只列欄名，還標了每欄的**角色**：放樣本名的那欄會標 `meta: ["id"]` 或 `meta: ["sample"]`；放定序檔的欄會帶「檔名必須是 `.fastq.gz`」的格式規則。所以「哪一欄放什麼」可以從管線自己的說明檔讀出來，不必寫死在我們的程式裡。

## Clarifications

### Session 2026-10-02

- Q: 說明檔看不出唯一答案時（例如 ampliseq 同時接受兩套欄名、mag 和 bacass 還有長讀欄位），怎麼辦？ → A: 停下來，列出候選欄位，請操作者指定；不猜。
- Q: 長讀（long reads）、組裝序列（fasta）這類其他檔案欄位要一起自動填嗎？ → A: 這次只處理短讀的 R1／R2；其他檔案欄位留空並提醒操作者補，另案處理。

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 任何管線的樣本表都填對欄位（Priority: P1）

操作者要跑一條沒跑過的 nf-core 管線。plugin 讀這條管線自己的輸入說明檔，判斷哪一欄放樣本名、哪兩欄放 R1／R2，把掃到的定序檔填進正確的欄位。操作者不需要知道這條管線怎麼命名欄位，也不需要找維護者。

**Why this priority**: 這是第 6、7 條被違反的核心。

**Independent Test**: 用 rnaseq、ampliseq、bacass、mag 四條管線真實的說明檔，各對同一個資料夾產生樣本表，樣本名和 R1／R2 都落在該管線自己的欄位。

**Acceptance Scenarios**:

1. **Given** rnaseq 的說明檔（`sample`／`fastq_1`／`fastq_2`），**When** 產生樣本表，**Then** 結果跟現在完全一樣。（正常；不能改壞現有行為）
2. **Given** 一條欄名不同的管線（例如 ampliseq 只要 `sampleID,forwardReads,reverseReads`；說明檔共有 4 個定序檔欄），**When** 產生樣本表，**Then** 因為說明檔有超過兩個定序檔欄，不論只要求哪幾欄都停下來不寫檔，列出要求的定序檔欄請操作者指定；操作者用 `--roles` 指定後，樣本名填進 `sampleID`、R1 填進 `forwardReads`、R2 填進 `reverseReads`。（例外）
3. **Given** 說明檔裡可能放定序檔的欄位超過兩個（ampliseq 兩套欄名都要、mag 有 `long_reads`、bacass 有 `LongFastQ`），**When** 產生樣本表，**Then** 停下來不寫檔，列出候選欄位，請操作者指定哪欄是 R1、哪欄是 R2。（例外）
4. **Given** 說明檔裡沒有任何一欄標成樣本名，或標成樣本名的欄位不只一個，**When** 產生樣本表，**Then** 停下來不寫檔，列出候選，請操作者指定。（例外）
5. **Given** 操作者已經指定了角色（哪欄是樣本名、R1、R2），**When** 產生樣本表，**Then** 照指定的填，不再自己判斷；指定的欄位不在這張表裡時，拒絕並說明。（正常／例外）
6. **Given** 拿不到說明檔（管線沒有 `schema_input.json`，或讀取失敗），而操作者也沒有指定角色，**When** 產生樣本表，**Then** 停下來說明原因並請操作者指定，而不是退回假設 rnaseq 的欄名。（例外）
7. **Given** 說明檔要求的其他檔案欄位（長讀、fasta、Fast5…），**When** 產生樣本表，**Then** 這些欄留空，並明講哪幾欄需要操作者補。（不在範圍：本次只自動填短讀 R1／R2）

### User Story 2 — 開始設定前就看得到「哪一欄放什麼」（Priority: P2）

送出前的總覽（`scripts/prepare_launch.sh` 的樣本表段落）除了列出欄名，也列出判斷出的角色：哪欄是樣本名、哪欄是 R1／R2；判斷不出時直接寫「需要你指定」以及候選欄位。操作者在第一步就知道會不會卡，而不是做到一半才發現。

**Why this priority**: 讓問題提早浮現；但先要能填對（US1）。

**Acceptance Scenarios**:

1. **Given** 一條角色判斷得出來的管線，**When** 看送出前的總覽，**Then** 樣本表段落列出 `樣本名 → <欄>`、`R1 → <欄>`、`R2 → <欄>`。（正常）
2. **Given** 一條判斷不出來的管線，**When** 看總覽，**Then** 樣本表段落寫明需要操作者指定，並列出候選欄位。（例外）

## Requirements *(mandatory)*

- **FR-001**: 樣本名欄與 R1／R2 欄 MUST 從管線自己的輸入說明檔判斷，plugin 程式裡不得寫死任何管線的欄名。
- **FR-002**: 判斷規則：樣本名欄＝要求的欄位中，唯一一個 `meta` 含 `id` 或 `sample` 的欄；定序檔欄＝要求的欄位中，格式規則只接受 FASTQ 檔名的欄，依說明檔裡的順序，第一個是 R1、第二個是 R2。
- **FR-003**: 判斷不出唯一答案時（樣本名欄 0 個或超過 1 個；定序檔欄超過 2 個），MUST 停下來、不寫檔、列出候選欄位並請操作者指定。
- **FR-004**: 操作者 MUST 能明確指定三個角色；有指定時以指定為準。指定的欄位不在要求的欄位中時 MUST 拒絕。
- **FR-005**: 拿不到說明檔、也沒有指定角色時，MUST 停下來說明，不得退回任何預設欄名。
- **FR-006**: 只有一個定序檔欄時，視為單端（single-end）欄位；但沿用現有規則——只有操作者說這批是單端時才寫成單端，否則照舊拒絕並詢問。
- **FR-007**: 短讀 R1／R2 以外的檔案欄位留空，並 MUST 明講哪幾欄需要操作者補。
- **FR-008**: 送出前的總覽 MUST 顯示判斷出的角色，或「需要你指定」與候選欄位。
- **FR-009**: 現有的 rnaseq 行為（欄名、內容、單端／雙端規則、警告）MUST 不變。

## 不在範圍

1. 自動填長讀、fasta、Fast5、BAM 等短讀 R1／R2 以外的檔案欄位（留空並提醒；另案）。
2. 從檔名推斷條件、批次、病人等中繼資料（launch.md 已規定要問使用者，不變）。
3. 公開資料庫來源（SRA／GEO），那條路走 nf-core/fetchngs，不經過這支工具（不變）。

## Success Criteria

- **SC-001**: rnaseq 以及任何「說明檔裡一欄樣本名＋最多兩欄 FASTQ」的管線，不需要指定也不需要維護者，就能產生欄位正確的樣本表。
- **SC-002**: 判斷不出來的管線，沒有任何一種情況會寫出欄位填錯的樣本表——一定停下來問。
- **SC-003**: plugin 程式碼裡不再出現任何管線專屬的欄名（以測試掃描確認）。

## Assumptions

- nf-core 管線的說明檔在要求的版本上可以讀到（`prepare_launch.sh` 已經在抓它）。
- 「格式規則只接受 FASTQ 檔名」以說明檔欄位的 `pattern`（含 `anyOf` 裡的）是否要求 `.fastq`／`.fq` 結尾判斷；`format: file-path` 本身不足以判斷（fasta、BAM 也是 file-path）。
