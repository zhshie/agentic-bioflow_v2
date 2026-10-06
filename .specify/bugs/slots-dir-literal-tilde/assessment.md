# Bug Assessment: on_site.sh under the WSL bridge creates a literal `~` directory in the caller's cwd

- **Slug**: slots-dir-literal-tilde
- **Created**: 2026-10-05
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/25
- **Verdict**: valid
- **Severity**: medium (clutter in whatever folder the caller is in, and the per-session cap is counted per caller directory, so it is not the cap the site enforces)

## 給維護者

1. 在 Git Bash 用 WSL 橋接時，`on_site.sh` 會在「呼叫它的那個資料夾」裡建出一個名字就叫 `~` 的資料夾（裡面是 `.ssh/cm-%r-%h-%p.slots`）。
2. 原因：交給 WSL 的 ControlPath 刻意保留字面的 `~/...`（讓 WSL 自己展開），但「同時間最多幾個 ssh 工作階段」的鎖資料夾是從同一個字串蓋出來、由 Git Bash 自己建，而 Git Bash 不會展開加引號的 `~`。
3. 後果不只是亂：兩個從不同資料夾呼叫的人各算各的，上限就不是站台真正的上限（PITFALLS 16e）。
4. 修法：鎖資料夾改用本機已展開的 `$HOME` 蓋；交給 WSL 的 ControlPath 不動。
5. 主 checkout 根目錄那個 2026-09-30 留下的 `~/.ssh/cm-%r-%h-%p.slots/` 是這個 bug 的殘留，我沒有刪，由你決定。

## Reproduction (Git Bash, main 2dfedd1; `C:\Users\ACER\abf_audit2\r25.sh`)

`reach: ssh`, `site_bridge: wsl`, a fake ssh, run `on_site.sh true` from an empty directory: the directory afterwards contains `~/.ssh/cm-%r-%h-%p.slots/`.

## Root Cause (high confidence)

`scripts/on_site.sh`: `SLOTS_DIR="${CP}.slots"` and `mkdir -p "$SLOTS_DIR"` in `acquire_slot`. `CP` is the ControlPath handed to ssh; under the bridge `site_control_path_default wsl` returns the literal `~/.ssh/cm-%r-%h-%p` on purpose (PITFALLS 16b). The lock directory is local, so it needs the local expanded path, not the string meant for the far side of `wsl.exe`.

## Proposed Remediation

Derive `SLOTS_DIR` from `CP` with a leading `~/` replaced by this shell's `$HOME`; leave `CP` itself untouched. Test in `tests/on_site_parallel_test.sh`: with a temp `$HOME`, the caller's directory is untouched after calls from two different directories, and the slot lock is seen under `$HOME/.ssh/cm-%r-%h-%p.slots`.
