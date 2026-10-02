# Bug Assessment: the walkthrough gate denies commands that only mention a step in quoted text

- **Slug**: walkthrough-quoted-text
- **Created**: 2026-10-01
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/42
- **Verdict**: valid
- **Severity**: medium (a false deny, never a false allow; it blocks ordinary maintenance and reporting commands — issue comments, commit messages — and teaches people to route around the gate)

## 給維護者

1. 導覽關卡（「先給使用者看流程圖、再做樣本表」那道）會把**引號裡的文字**也當成真的動作：一則 issue 留言、一個 commit 訊息只要提到產生樣本表的腳本名稱，就被擋下來。
2. 只會多擋、不會放行；但它擋的是日常的回報與記錄，久了大家會學會繞過它。
3. 修法跟 #29 一樣：用共用的指令切割器，看「引號外」的文字；只有引號裡的字、而且那個指令本身不會執行任何東西（echo、git、gh…）時才放行。
4. 刻意保留：腳本路徑加引號（`python3 "scripts/generate_samplesheet.py"`）、寫入加引號的 `"params.yml"`、把指令餵給 shell 的 here-doc，這些仍然要擋——002 驗收學到的教訓是，引號外判斷會漏掉加引號的路徑。

## Reproduction (WSL, main 0b8cd3c, empty transcript)

| Command | Verdict | Should be |
|---|---|---|
| `gh issue comment 31 --body "generate_samplesheet.py decides column roles"` | **deny** | allow |
| `git commit -m "fix: fastq_dir_to_samplesheet handles column roles"` | **deny** | allow |
| `git commit -m "docs: cat > params.yml example"` | **deny** | allow |
| `echo "tw datasets add x"` | **deny** | allow |
| `python3 scripts/generate_samplesheet.py --input x` | deny | deny |
| `tw datasets add x` | deny | deny |

The issue's own example (`--body "... samplesheet column roles ..."`) is allowed on current main by itself; it was denied because that body named the generator script.

## Root Cause (high confidence)

`hooks/confirm_walkthrough.sh`, the Bash branch of the gate selection (G1 samplesheet, G2 params file), runs `grep -qE` over the raw command line — quoted arguments included. G4 (analysis code) already strips here-doc bodies; neither uses `hooks/split_segments.awk`'s quote-free column, which #29 introduced for exactly this class of problem in the deletion and launch gates.

## Proposed Remediation

Per segment of the shared splitter (on the command with here-doc bodies stripped):
- G1/G2 fire when the pattern matches the **quote-free** column (as today, minus quoted text).
- They also fire when the pattern only matches once quotes are dropped **and** the segment's command word runs something (a shell, python, `tw`, `env`/`exec`/`xargs`/… wrappers) — a quoted script path is still a run. For G2, a real redirect (`>` outside quotes) with a quoted `"params.yml"` target also fires.
- A here-doc whose body is fed to a shell or python (`bash <<EOF`, `python3 - <<EOF`) is judged on its body as before.
- Tests first in `tests/confirm_walkthrough_test.sh`: the four false denies above must allow; the two real ones, a quoted script path, a quoted params target, and `bash <<EOF` with the generator inside must still deny.
- Out of scope: G3 (launch verbs, shared with confirm_launch.sh and already splitter-based) and G4.
