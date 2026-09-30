# Implementation Plan: 對外白名單可由部署自己擴充

**Branch**: `002-relay-allowlist` | **Date**: 2026-09-30 | **Spec**: `spec.md` | **Test cases**: `test-case.md` (23, approved 2026-09-30)

## 給維護者：複雜度與風險摘要（人工關卡 2）

**做法一句話**：每位成員的設定資料夾裡多一個小檔案，記錄自己額外放行的網域（連同日期與原因）；啟動中繼程式時，把這份清單跟其他設定一樣帶到叢集上，中繼程式放行「內建＋額外」。加入／移除都用一支新腳本，而且會被安全網攔下來請你確認。

**複雜度**：小到中。一支新腳本、改中繼程式讀清單的地方、安全網加一條規則、兩個指令檔改一句話。不改「誰能連進中繼程式」那一半。

**分三段做**，每段結束全部測試綠燈：
1. 新腳本 `scripts/egress_allow.sh`：加入、移除、列出、檢查網域格式、必填原因。
2. 中繼程式讀額外清單、啟動時分兩組列出、清單壞掉時照常啟動並說明。
3. 安全網：加入／移除要你確認；`runs.md`／`launch.md` 改成指向這支腳本。
之後由獨立 agent 驗收，最後要你手動試一次 TC-013，並在真的叢集上加一個網域試跑（第 4 項風險）。

**風險（由高到低）**：
1. **放寬了安全邊界的操作權**：以前只有維護者能放行網域，之後每位成員都能放行自己的。靠三件事守住：一定要你按確認、一定要寫原因、只接受具體網域（不接受 `*`、IP、整個 `.com`）。
2. **格式檢查漏網**：例如 `evil.com.` 結尾有點、大小寫、國際化網域。測試案例會涵蓋，驗收也會專挑這裡。
3. **帶到叢集的方式**：清單是透過環境變數帶過去的，網域很多時可能太長。實務上一個部署大概只會加幾個到十幾個，計畫裡設上限 100 個，超過就拒絕並說明。
4. **只在假環境測過**：中繼程式真正放行與否，要在真叢集上看一次（第 3 段後的手動步驟）。

## Technical Context

- Bash (scripts, hooks) + Python 3 stdlib (`scripts/nf_relay.py`); no new dependency.
- Storage: `<root>/config/egress_allow.tsv` — one line per domain: `domain<TAB>YYYY-MM-DD<TAB>reason`. In the settings root, so it travels with the root and survives plugin updates (FR-001, SC-002); per deployment (FR-010). Location from `settings.sh` (`config_dir`), never hard-coded (invariant 3).
- Transport: `scripts/on_site.sh` already carries the few values site scripts need as environment variables (`carry NF_RELAY_PORT …`). Add `carry NF_RELAY_EXTRA_DOMAINS "<comma list>"` and `carry NF_RELAY_EXTRA_NOTE "<why the list is empty or partial>"`. Under `reach: local` the same variables are exported directly.
- Tests: bash, repo style; the relay's matching is tested by importing `nf_relay.py` functions with the environment set (no network).

## Constitution Check (PASS)

| Principle | How |
|---|---|
| 1 | `egress_allow.sh` header: `# Nothing existing: …` (no maintained tool manages this relay's list); TC-021 |
| 2 | No run state stored; the list is configuration |
| 3 | Path from the settings root; TC-020 |
| 4 | Commands say "allow it through the outbound channel" and call `scripts/egress_allow.sh` via the adapter's own wording; `nf_relay`/`relay` never named in `commands/`; TC-022 |
| 6, 7 | The whole point: a new pipeline's domain no longer needs the maintainer |
| 8 | Real-cluster check after stage 3 |
| 11 | The file is owner-only like the rest of `config/` (existing read-back applies) |
| 13 | A broken list is said out loud (TC-008/009/023) |
| Safety Net | Adding/removing asks (TC-007/016); the peer restriction is untouched (TC-019) |

## Design

### `scripts/egress_allow.sh` (new)

```
egress_allow.sh add <domain> --reason "<text>"   # validates, appends with today's date
egress_allow.sh remove <domain>
egress_allow.sh list                             # domain, date, reason ("來源不明" if missing)
egress_allow.sh domains                          # comma list for on_site.sh to carry; warnings on stderr
```

Validation (FR-004): lowercase; strip one trailing `.`; must match `^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$` (at least two labels); reject IP literals, `*`, empty; at most 100 entries. `--reason` required and non-empty (TC-018). Duplicate add → says already present. The script never restarts the relay; it says the next step is restarting the outbound channel (which asks, per the existing gate).

### `scripts/nf_relay.py`

`EXTRA_DOMAINS` parsed from `NF_RELAY_EXTRA_DOMAINS` with the same validation; invalid entries dropped and each named in the startup log; `domain_ok` checks `ALLOW_DOMAINS + EXTRA_DOMAINS`. Startup log: `domains (built in): …` / `domains (this deployment): …` or `this deployment's list not loaded: <NF_RELAY_EXTRA_NOTE>` (TC-004, 008, 009, 023). `ALLOW_HOST_PREFIXES` / peer check untouched (TC-019).

### `hooks/confirm_launch.sh`

A rule beside the resident-process gate: a segment whose command runs `egress_allow.sh add|remove` → ask, naming the domain and reason and that this moves a security boundary on a shared login node (TC-007, 016). Uses the shared splitter (quote-free column, #29).

### Commands

`commands/runs.md` and `commands/launch.md`: "Once approved: allow it, restart the outbound channel, relaunch" → name `scripts/egress_allow.sh add <host> --reason …`, then the existing restart step. A request to add to the built-in list → explain it is the maintainer's change (TC-013).

## Stages (each ends with `tests/run_all.sh` green in WSL)

| Stage | Delivers | Test cases |
|---|---|---|
| S1 | `egress_allow.sh`, settings path, `list` display | TC-001, 005, 006, 014, 015, 017, 018, 020, 021 |
| S2 | relay reads the list; on_site carries it | TC-002, 003, 004, 008, 009, 010, 011, 019, 023 |
| S3 | hook gate; command wording | TC-007, 012, 016, 022 |
| Manual | TC-013; add one domain on the real cluster and relaunch | TC-013 |

## Project Structure

```text
scripts/egress_allow.sh          (new)
scripts/nf_relay.py              (reads NF_RELAY_EXTRA_DOMAINS)
scripts/on_site.sh               (carries it)
hooks/confirm_launch.sh          (asks on add/remove)
commands/runs.md, commands/launch.md
docs/SETTINGS.md                 (the new file), docs/SITE_ADAPTER.md (egress contract mentions the per-deployment list)
tests/egress_allow_test.sh       (new), tests/confirm_launch_test.sh, tests/nf_relay_* (existing relay tests extended)
```
