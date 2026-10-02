# Bug Assessment: 005 scope check calls four low-severity shapes "not in use"

- **Slug**: scope-shapes
- **Created**: 2026-10-02
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/53
- **Verdict**: valid
- **Severity**: low (each shape is one main's always-on gates still refused; the scope check now lets it through only in a session with no plugin marker, a cwd outside the deployment, and a command that does not name the deployment as written)

## 給維護者

1. 005 的「這個 session 有沒有在用 plugin」判斷有四個小洞，每個都是「舊版一律擋、現在判成沒在用而放行」。
2. 都要同時滿足：沒有 marker、工作資料夾在部署外、指令沒用能辨認的寫法指到部署資料夾，才會漏。
3. 修法一律往「寧可多判成在用」的方向：引號內的 `"$HOME"` 當作 `$HOME`；單獨的 `cd` 之後走相對路徑，而部署根目錄在家目錄底下時當作在用；沒有斜線的 `agentic-bioflow:launch` 也寫 marker；ssh 的 `-F cfg` 讓 BatchMode 豁免失效。
4. 讀不到 `~/.ssh/config` 這件事無法修，只能在 D3 註解寫明。

## Items (each is a test case)

| # | Shape | Today | Test |
|---|---|---|---|
| 1 | `cd "$HOME"/runs3 && rm -rf results` (also `"${HOME}"`) | silent | `tests/in_use_test.sh` "#53 a quoted ..." deny |
| 2 | `cd && cd runs3 && rm -rf results` (also `cd ~`, `cd $HOME`) | silent | "#53 a bare cd ..." deny; controls: no root under home, cd elsewhere, `echo cdrom` stay silent |
| 3 | `ssh -o BatchMode=yes -F cfg host cmd` (config may carry ProxyJump) | exempt, no ask | `tests/confirm_launch_test.sh` "#53 -F cfg", "-Fcfg", "scp -F" ask; control without -F still exempt. The default `~/.ssh/config` cannot be seen by a hook: one line in the D3 comment |
| 4 | prompt "...with agentic-bioflow:launch" (no slash) | no marker | "#53 a prompt naming agentic-bioflow:launch without a slash marks"; control: the name without a colon marks nothing |

## Root cause

1. `hooks/in_use.sh` turns the call's JSON text into paths by turning every backslash into a slash. A JSON-escaped quote (`\"`) therefore became `/"`, so `"$HOME"/runs3` read as `/"/home/u/"/runs3`, which names nothing.
2. The text check only matches a root as written. A relative `cd` chain from home never contains the root's path.
3. `batchmode_exempt` in `hooks/confirm_launch.sh` already refuses `-J`, `ProxyJump`, `ProxyCommand`; it treats `-F <file>` as an ordinary option, but a named config file can set a ProxyJump.
4. `hooks/plugin_intro.sh` writes the marker for a mid-prompt mention only when it contains `/agentic-bioflow:`.

## Scope / fix direction

- `in_use.sh`: drop JSON-escaped double quotes and single quotes from the text before paths are compared (only widens what matches). A bare `cd` (alone, `cd ~`, `cd $HOME`) with a deployment base at or under home counts as in use (widening; the in-use answer only matters when the command is already gate-shaped, so the cost is a gate that applies, never a new refusal of an ordinary command).
- `confirm_launch.sh`: `-F` (separate or glued) makes the BatchMode exemption not apply; D3 comment names `~/.ssh/config`.
- `plugin_intro.sh`: any `agentic-bioflow:` in a user prompt marks the session.

## NOT changed

- The overview is still shown only when a prompt starts with the slash form.
- Nothing else in D3 (WSL exemption stays; ssh run through WSL can also read a config, unseen, same comment).
- No change to what any gate refuses once the session is in use.
