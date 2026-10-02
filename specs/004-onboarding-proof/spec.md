# Feature Specification: 新電腦、第二位成員也要先用公開資料驗證（onboarding proof）

**Feature Branch**: `004-onboarding-proof`

**Created**: 2026-10-02

**Status**: Draft

**Input**: 憲法稽核 C 批（#31）第三件。以下兩條捷徑讓人沒跑過公開測試資料就拿到指令清單：
- `commands/setup.md` 開頭的 T27 規則：`scripts/setup_verify.sh` 只要 `preflight.sh` 通過就說「這台已經設定好」並結束 setup。
- 新電腦用 `settings.sh --use <root>` 沿用舊設定後「直接跳到 Repair」，而 Repair 不跑驗證。

結果是一台從沒跑過公開測試資料的電腦可以直接開始 launch 真實資料。這違反第 7 條：onboarding MUST 先用公開測試資料證明環境可用，不碰使用者的資料，然後才交出指令清單。

> 名詞見 `CONTEXT.md`。本規格給維護者看，用中文；編號照 Spec Kit 慣例。
> 稽核 C 批另兩件：白名單（002，已 merge）、樣本表欄位（003）。

## 背景

setup 第 8 步跑兩個公開測試 run：`nextflow-io/hello` 和 `nf-core/demo -profile test`。第 9 步規定「第 8 步通過之前不准介紹 launch／runs」。可是**沒有任何地方記錄第 8 步在這台電腦上通過過**，所以下列兩條捷徑都跳過了它：
- 「已經設定好」的判斷只看 `preflight.sh`，而 `preflight.sh` 只檢查連線和設定。
- 「沿用設定」直接進 Repair。

設定本來就分成兩層：
- **跟著人走**：`config/env.yaml`。
- **只屬於這台電腦**：`config/machines/<這台>.yaml`，Git Bash 和 WSL 也算兩台。

「這台電腦證明過」天生屬於第二層。換新電腦時，那台沒有紀錄；第二位成員有自己的設定根目錄，也從零開始。

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 沒證明過的電腦拿不到指令清單（Priority: P1）

同一個人換了新電腦，或第二位成員加入，或舊電腦設定齊全但從沒留下證明。setup 都會先用公開測試資料跑一次證明，通過後才介紹 launch／runs。

**Why this priority**: 這就是第 7 條被違反的地方。

**Independent Test**: 用假的 `preflight.sh` 和假的 `tw` 建一台「設定齊全、沒有證明紀錄」的電腦，`setup_verify.sh` 不回「已經設定好」；記錄一個合格的 run 之後才回。

**Acceptance Scenarios**:

1. **Given** 這台電腦 preflight 通過，而且有證明紀錄，**When** 跑 `setup_verify.sh`，**Then** 回「已經設定好」（exit 0），並附上證明是哪個 run、哪天。（正常）
2. **Given** preflight 通過但這台電腦沒有證明紀錄（新電腦沿用舊設定，或舊版裝的電腦），**When** 跑 `setup_verify.sh`，**Then** 不說「已經設定好」，改說「設定齊全，但這台還沒用公開測試資料證明過」，並指向第 8 步（exit 3，跟「需要修」的 exit 1 分開）。（例外）
3. **Given** 同一個設定根目錄被另一台電腦用過、那台有證明紀錄，**When** 在這台跑 `setup_verify.sh`，**Then** 那台的紀錄不算數（exit 3）。（例外）
4. **Given** 第 8 步的 `nf-core/demo` run 在 Platform 上狀態是成功、而且是這個人送的，**When** 用該 run 的 ID 記錄證明，**Then** 寫進這台電腦自己的設定檔，並印出記下了什麼。（正常）
5. **Given** 要記錄的 run 不是成功狀態（失敗、取消、還在跑），或不是 `nf-core/demo`，或是別人送的，或在 Platform 上找不到，**When** 記錄證明，**Then** 拒絕寫入並說明是哪一項不符。（例外）
6. **Given** 連不上 Platform（`tw` 失敗），**When** 記錄證明，**Then** 拒絕寫入，說明無法確認，不得當成通過。（例外）
7. **Given** 設定還不齊（preflight 失敗）或根本沒有設定檔，**When** 跑 `setup_verify.sh`，**Then** 行為跟現在一樣（exit 1，進 repair 或 first run）。（正常；不能改壞）

### User Story 2 — setup 的說明照新規則走（Priority: P1）

`commands/setup.md` 必須把三個入口都導到第 8 步，第 9 步只在證明記下之後才介紹指令：「已經設定好」、「沿用設定後進 Repair」、first run。

**Acceptance Scenarios**:

1. **Given** `setup_verify.sh` 回 exit 3，**When** agent 照 setup.md 走，**Then** 直接做第 8 步（公開測試資料），然後第 9、10 步，不重做第 1–7 步。（正常）
2. **Given** 沿用設定（`--use`）後進 Repair，**When** Repair 修完，**Then** 檢查這台有沒有證明，沒有就做第 8 步，再介紹指令。（正常）
3. **Given** 第 8 步，**When** `nf-core/demo` 成功，**Then** setup.md 要求執行記錄證明的指令，第 9 步只在記錄成功後才進行。（正常）

## Requirements *(mandatory)*

- **FR-001**: 「這台電腦已用公開測試資料證明過」MUST 存在這台電腦自己的設定檔（`config/machines/<這台>.yaml`），不得存在跟著人走的 `config/env.yaml`。
- **FR-002**: 新增 `scripts/setup_proof.sh`。
  - `--check`：有紀錄 exit 0 並印出紀錄；沒有紀錄 exit 1。
  - `--record <run-id>`：向 Platform 查這個 run，確認下列四項都成立才寫入紀錄（run ID ＋日期）：
    1. 狀態是 `SUCCEEDED`。
    2. 管線是 `nf-core/demo`。
    3. 送出者是設定裡的 `seqera_user`（設定裡有這個值時）。
    4. 存在於設定裡的 workspace。
  5. 7 天內送出的（驗收後加）。
  6. 沒有被同一設定根目錄下的另一台電腦拿去當證明（驗收後加）。
  - 任一項不符或查不到，都 MUST 拒絕並說明是哪一項。
- **FR-003**: `setup_verify.sh` 只在 preflight 通過**而且**這台有證明紀錄時才 exit 0。preflight 通過但沒有紀錄時 MUST exit 3，並說明「還沒證明、去第 8 步」。其他情況維持現狀（exit 1）。
- **FR-004**: 記錄證明只接受 Platform 上查得到的事實；連不上或格式讀不懂時 MUST 拒絕，不得當成通過。
- **FR-005**: `commands/setup.md` MUST 把 exit 3 和「沿用設定後 Repair 結束」都導向第 8 步。第 8 步 MUST 以記錄證明作結；第 9 步 MUST 寫明只在記錄成功後才介紹指令。
- **FR-006**: `docs/SETTINGS.md` MUST 記載新的這台電腦專屬設定值（名稱、誰寫的、為什麼不跟著人走）。
- **FR-007**: 現有行為不變：沒有設定檔、preflight 失敗、repair 流程、first run 第 1–7 步都不變。

## 不在範圍

1. launch 本身不檢查證明紀錄。憲法要求的是 onboarding 在交出指令清單前證明；在 launch 擋人會讓已在用的電腦突然不能用，要另案討論。
2. 環境改變後（換 compute environment、換叢集）讓舊證明失效。這次只處理「從沒證明過」。
3. 自動送出證明用的 run。送出仍由 agent 照第 8 步做，經過既有的 launch 確認關卡。

## Success Criteria

- **SC-001**: 任何一台電腦，只要沒有自己這台的證明紀錄，就不會被 setup 說成「已經設定好」，也不會在 setup 裡拿到 launch／runs 的介紹。
- **SC-002**: 證明紀錄只能由一個在 Platform 上查得到、成功、屬於這個人的 `nf-core/demo` run 寫入。

## Assumptions

- `tw -o json runs list --workspace <ws>` 的格式：每筆在 `.workflows[].workflow` 底下，有 `id`、`projectName`、`status`、`userName`。這是 `scripts/runs_board.sh` 2026-09-18 實測過的格式，本功能沿用它，不另做假設。
- 已在用的電腦（例如維護者自己的）下次跑 setup 會被要求補一次證明。這是預期的，因為它們確實沒留下過證明。
