# Bug Assessment: a slow plugin_intro.sh can be killed before it writes the in-use marker

- **Slug**: intro-marker-timeout
- **Created**: 2026-10-05
- **Source**: fresh audit against constitution 2.0.0 (`C:\Users\ACER\abf_audit2\tintro.sh`), Safety Net scope condition 1, invariant 13
- **Verdict**: valid
- **Severity**: high (a session that reached for the plugin can count as NOT in use: every gate then stays silent, with nothing said)

## 給維護者

1. `plugin_intro.sh` 在使用者第一次用 plugin 時做兩件事：寫下「這個 session 在用 plugin」的 marker（其他所有 hook 都靠它判斷要不要啟動安全網），以及顯示總覽。
2. hooks.json 只給它 5 秒；原生 Git Bash 上量到 3.5–6.6 秒。超時會被砍掉。marker 寫在幾個外部程式（`cat`、`tr`、`jq`、`find`）之後——技能載入那條路甚至要先跑兩次 `jq`——所以機器一忙，marker 可能根本沒寫，之後整個 session 的關卡都當作「沒在用」而不出聲。
3. 修法：一進來、還沒開任何程式之前就判斷「是不是在用 plugin」並寫 marker（直接比對原始輸入文字，不靠 jq）；少開程式（不用 `cat`、短輸入不用 `tr`、資料夾已在就不 `mkdir`、清舊 marker 的 `find` 一個 session 只跑一次）；hooks.json 改成實際的 20 秒。

## Reproduction

- Native Git Bash, HEAD 490de98, `tintro.sh` (audit, machine under load): 3.5-6.6 s per typed command against a 5 s timeout.
- Order in the hook: `INPUT=$(cat)`, `printf | tr` (NORM), then for a typed command `mark_in_use` (`mkdir -p`, `find`); for a skill load the marker comes only after `command -v jq`, `printf '{}' | jq -e .` and the EVENT `jq` call. With those tools made slow (each sleeps 20 s) and the hook under `timeout 3`, no marker is written for a typed command, a skill load or the natural-language door.

## Root Cause (high confidence)

`hooks/plugin_intro.sh` decides "is this the plugin being used" after starting external programs, and writes the marker after that; `mark_in_use` itself runs `mkdir -p` and a `find ... -exec rm` sweep every time. hooks.json's 5 s was set when this was a SessionStart overview, before the marker existed.

## Scope / fix direction

- Read stdin without `cat`; decide the literal doors on the raw text by bash regex (a typed `agentic-bioflow:` in a UserPromptSubmit prompt; a Skill input whose `skill` starts with `agentic-bioflow:`) and write the marker first. The natural-language door folds the text in the shell for a prompt under 8 KB (no `tr`), then marks.
- `mark_in_use`: no `mkdir` when the folder exists; the 30-day sweep runs once per session (when the marker is new), after the marker is written.
- hooks.json: 20 s for both plugin_intro.sh entries (UserPromptSubmit, PostToolUse Skill).
- Tests: `tests/plugin_intro_test.sh` - the marker exists after the hook is killed at 3 s with every external tool slow, or with intro.sh slow, for all three doors; a control (another plugin's skill naming this one) leaves none; hooks.json timeouts >= 15 s.

## NOT changed

- When the overview is shown, what it says, and the once-per-session rule.
- The precise jq check of the event before the overview is shown.
