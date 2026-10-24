# 轉送警告補強：最後一個指派為準、豁免縮窄、共用 helper progress ledger

- [x] RED a3b34cc: tests/confirm_launch_test.sh adds `envw` + RWH-1..26 (45 rows); 42 failed before the hook change.
- [x] GREEN: hooks/confirm_launch.sh adds `relay_env_warn` (after `ask()`, before RESIDENT block); the two warning blocks now call it. `bash tests/confirm_launch_test.sh` -> all passed (WSL).
- [x] RWH-23's negative check looks at the `SETS` line (the ask also echoes the command itself, which holds 250 x).

## Evidence (done-when)
- Scope: only hooks/confirm_launch.sh, tests/confirm_launch_test.sh, this ledger changed (scripts/, platform/, docs/, skills/ untouched).
- Reworded existing assertions (5), before -> after (only the required string):
  1. PEER-3: `${PW_SETS}25a-cpn, which changes` -> `${PW_SETS}25a-cpn, which asks the relay to use this list of host-name prefixes`
  2. PEER-4: `${PW_SETS}, which changes` -> `${PW_SETS}, which asks the relay to use this list of host-name prefixes`
  3. PEER-7 value: `${PW_SETS}25a-cpn,25a-lgn, which changes` -> `...which asks the relay to use this list of host-name prefixes`
  4. PEER-7 which hosts: `which changes which hosts may connect to the relay` -> `for the hosts that may connect, instead of the deployment's setting`
  5. PEER-7 default list: `instead of the deployment's setting (default cpn,gpn,bgm,lgn,localhost)` -> `falls back to the built-in one`
- Both branches: `tests/confirm_launch_test.sh` on origin/v3 (git archive) = all passed; on this branch = all passed. Line diff after squeezing spaces: only the new RWH rows plus the changed "idg ... N behind a big here-doc" count line (116 -> higher).
- Not weaker: 48 commands (all RWH commands, EXTRA/PEER shapes, egress_ctl start|stop|restart|status, agent_ctl start, ls, NF_RELAY_PORT, NF_RELAY_EXTRA_NOTE, indirect export) fed to old and new hook: old ask 46, new ask 46, none went ask -> allow. status and ls allow on both.
- Cost (WSL, ~100 KB command): no variable: base 0.101 s, new 0.114 s (noise); 25 assignments + 3 start points: base 0.101 s, new 0.284 s (hooks.json timeout is 30 s).
- Helper body check (sed -n of `relay_env_warn`, grep for grep/jq/python/sed/awk/tr/mktemp/eval and command substitution): no command substitution; the only `$(` hits are `$((...))` arithmetic and string literals used as patterns. `grep -c 'cpn,gpn,bgm,lgn,localhost' hooks/confirm_launch.sh` = 0.
- Empty-value sentence ("An empty value is ignored by the relay, which then uses the deployment's relay_peer_prefixes setting.") kept word for word; shown when the last value is empty.
- Known/accepted: quoted `scripts/on_site.sh --script "${CLAUDE_PLUGIN_ROOT}/scripts/egress_ctl.sh" start` gets one extra warning (quote between on_site.sh and egress_ctl.sh); accepted per ruling 6.
- Not done (other task): indirect assignments (`export $V=...`, `printf -v`, `env -S`) are not detected, same as before.
- Design note: start points are checked per command segment (the last one in each segment decides, since a quote after on_site.sh before a later start also lies before the earlier one's tail); at most 8 segments, 20 assignments (last 20 read), past that it warns.
