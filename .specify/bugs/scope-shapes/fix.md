# Fix: scope-shapes (#53)

- **Branch**: `fix/53-scope-shapes`
- **Changed**: `hooks/in_use.sh`, `hooks/plugin_intro.sh`, `hooks/confirm_launch.sh` (D3), `tests/in_use_test.sh`, `tests/confirm_launch_test.sh`
- **What changed**
  1. `in_use.sh` drops JSON-escaped double quotes and single quotes from the call text before comparing paths, so `"$HOME"/runs3` and `"${HOME}"/runs3/p` name the root.
  2. `in_use.sh`: a `cd` with no destination (or `cd ~`, `cd $HOME`) counts as a walk from home; if a deployment root, storage_root or runs dir is at or under home, the call is in use. A plain `cd /tmp`, `echo cdrom`, or a deployment outside home stays silent.
  3. `plugin_intro.sh`: a prompt containing `agentic-bioflow:` anywhere (slash or not) writes the in-use marker. The overview still needs the leading slash.
  4. `confirm_launch.sh` D3: `-F <file>` (separate, glued, or in a cluster) makes the BatchMode exemption not apply; the comment names the unseen `~/.ssh/config` ProxyJump/ProxyCommand blind spot.
- **Red -> green**: `tests/in_use_test.sh` 6 red before (quoted HOME x2, bare cd x3, no-slash prompt), 0 after (one more case, the single-quoted absolute path, passed on main and is labelled a control). `tests/confirm_launch_test.sh` 3 red (`-F`, `-Fcfg`, `scp -F`), 0 after; control without `-F` stays exempt.
- **Compared with main**: every change only widens "in use" or narrows an exemption, so no gate goes quieter than main. Also green in WSL: confirm_cleanup, confirm_walkthrough, guard_plugin_files, session_start, next_step, plugin_intro, in_use_speed, constitution_scope.
- **Not fixed**: a ProxyJump in the default `~/.ssh/config` cannot be seen from a hook (comment only, as the issue asked). The `cd` rule is deliberately coarse (any root under home), not a real relative-path resolver.
- **Needs maintainer decision**: none (all choices are the widening direction).
