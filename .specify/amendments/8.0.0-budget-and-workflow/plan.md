# Plan: constitution 8.0.0 — a yes given in advance (BUDGET); three changes to the Development Workflow

Branch `feat/dev-mode-launch`, base `v3`. Tier A: the maintainer says yes in his own words before
anything merges (Governance); until then the pull request is a draft and the Approval field says
`PENDING`. Drafted on 2026-11-11. Part A's plan and test cases are `specs/dev-mode-launch/`
(`plan.md`, `test-case.md` TC-077 to TC-101); this file adds what that plan does not cover: part B
and the list of edits.

## 給維護者

1. **A（產品）**：你在設定頁填兩個數字（單次 SU 上限、每月 SU 上限）以後，AI 在國網送出的分析只要在兩個上限內，就不再逐次等你按好。沒填就跟今天一樣每次都問。雲端要花錢的、`forget`（刪紀錄）、清工作目錄，不管數字多大，永遠要你本人按。數字只有你本人登入後在設定頁能改，AI 改不了。
2. **A 比今天弱的地方**：你同意的是「一個額度」，不是「這一次」；預估是用以前成功的紀錄算的，可能不準。
3. **B（開發流程）**：(a) 實機驗收可以排在合併之後；(b) 失敗的任務可由裁決代理處理，但花錢、金鑰、權限、憲法、發版、受保護的 hooks 永遠回到你；(c) 受保護路徑的改動，有「對抗審通過」的書面紀錄才可以自動合併，修憲、發版、改掉既有需求、放寬安全網永遠不適用。
4. **B 裡面實質放寬的兩處**（請特別看）：(a) 讓 `v3` 可以先收下還沒在真機器上跑過的改動；(c) 拿掉「主導者親手合併」這一關，而受保護路徑正是安全網閘門所在的檔案，之後「這個改動有沒有放寬安全網」只靠對抗審判斷。
5. 你要決定的：A 全文好不好；B 的 (a)(b)(c) 各自好不好（可以只同意其中幾點）。

## 維護者的話

- 2026-10-13：「設計成在開發階段你可以自由送出，實際產品再改回來。取消直接開放」
- 2026-11-03：「開發模式讓 AI 直接送出是對的」
- 2026-11-07（主導者轉述，非逐字）：國網 SU 預算內 AI 送出免逐次確認；雲端花錢的動作永遠要確認；門檻由使用者在設定頁自己設（單次與每月 SU），沒設定就一律要確認。
- 2026-11-10（主導者轉述，非逐字）：開發流程一節的修正——實機驗收可在合併後；失敗可由裁決代理處理；受保護路徑經對抗審後可自動合併。
- 他尚未對 8.0.0 全文說好。Approval 欄只寫 `PENDING`。

## What changes

### 1. Constitution (`.specify/memory/constitution.md`)

- **Principle I.2**: after the sentence on stdio and HTTP callers, the BUDGET sentences (off until
  the person turns it on; two limits on the settings page; both set and above zero; estimate and
  the month's use inside the limits; everything else goes back to the four channels; cloud bills,
  `forget` and clearing a work directory never; hosted never; only the person sets the limits;
  weaker than a yes for each send). The sentence "The four are the only ones; …" is untouched.
- **Safety Net, launch rule**: one exception named, with its limits; `hooks/confirm_launch.sh` has
  none. The first sentence is untouched.
- **Safety Net, write-tool rule**: BUDGET named with what it never covers and that a caller cannot
  hand it in; the `(today …)` list is untouched; the Check line adds
  `platform/tests/test_budget_launch.py` (`test_bg_*`).
- **Development Workflow, last rule ("One change at a time, on a branch.")**: three additions
  (a) (b) (c) appended inside the same rule, so the number of rules stays eight and every 6.2.0
  sentence is kept word for word.
- **New record** `### 8.0.0 (2026-11-11): …` before `## Governance`, six sections; Approval is the
  PENDING sentence only.
- **Version line**: `**Version**: 8.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-11-11`.

No other Safety Net rule, no principle other than I.2, and no record from 2.0.0 to 7.0.0 changes.

### 2. Tests

- `tests/budget_doc_test.sh` (new): the version line, the record's shape, the PENDING Approval, each
  "never", the unchanged Safety Net rules, a fingerprint of the records 2.0.0 to 7.0.0, part B's
  limits, and four self-tests that prove it goes red.
- `tests/constitution_scope_test.sh`: version label and string, Last Amended, TC-E5 line,
  `PINNED_SN_SHA256` (`ee51f3e2…` → `8a59945b…`). Nothing else.
- `tests/platform_direction_docs_test.sh` (TC-001) and `tests/charter_v4_workflow_test.sh` (TC-028):
  the version line only.

### 3. Documents

`docs/PLATFORM.md` (one paragraph after the three MCP ways), `docs/PRINCIPLES.md` (one history
paragraph). `README.md`, `CLAUDE.md`, `docs/ROADMAP.md`, `CONTEXT.md` and the ADRs are not changed:
no pinned test asks for it and none of them restates the changed sentences.

## Part B against "the Safety Net only gets stricter"

| Point | Rewords a Safety Net rule? | What it loosens | What holds it |
|---|---|---|---|
| (a) real-site acceptance after the merge | no | `v3` may hold a change no real site has run | CI and the independent acceptance first; owed checks listed; not done, not released while owed; a failed check reopens |
| (b) ruling agent | no | the lead no longer rules on every failure | not the executor or reviewer of the task; written rulings; never money, credentials, permissions, constitution, release, protected hooks |
| (c) automatic merge of a protected path | no | the lead's merge by hand goes, for the files that carry the Safety Net's gates | written record of a passed adversarial review on the merged commit, by a third reviewer; never an amendment, release, changed requirement or loosening; doubt waits |

(c) is the one closest to loosening the Safety Net in practice, and the pull request says so in red.

## Out of scope

The ruling agent, the automatic merge and the list of protected paths live in the development
lead's workspace; nothing in `.github/`, `hooks/`, `plugin.json` or `platform/abf_station/` is
touched here. The second slice (automatic resume) is not built.

## Open points for the development lead

- `specs/dev-mode-launch/test-case.md` TC-081 limits the constitution diff to I.2, the Safety Net
  rules, the 8.0.0 record and the version line. Part B edits the Development Workflow on the
  instruction of the development lead (2026-11-11); TC-081 needs a ruling or a revised case.
- Part B has no test cases written by the independent reviewer. `tests/budget_doc_test.sh` holds
  its wording, but that test was written by the author of the amendment.
