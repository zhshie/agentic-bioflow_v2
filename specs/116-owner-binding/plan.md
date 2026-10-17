# Plan 116: every action sees and uses only the caller's own compute environments, agents, runs and files

- **Slug**: 116-owner-binding. **Branch**: `feat/116-owner-binding`, base **v3** (after #115, 009c)
- **Tier**: A (tightening). It makes ADR 0009's rule "each person sees only their own runs" true. No principle changes, and no deny is weakened.
- **Created**: 2026-10-17 by the developer-agent. The facts were gathered by a read-only Plan agent on the #115 head; re-check the line numbers on v3.

## 給維護者
1. 以後每個人只看得到、也只用得到自己的運算環境、代理、run 和上傳資料夾；別人的東西對他來說是「找不到」。
2. 每次送出都記下是誰送的；終端機送出要指明帳號（`--user 名字`）。沒記錄送出者的舊 run，網頁和 HTTP 看不到，只有本機終端機看得到。
3. 舊資料：平台只有一個使用者時全部歸他；兩個以上先不歸任何人（只有本機終端機能用），用指令指定。

## Facts (verify on v3)
- The read actions ignore the caller: `actions/__init__.py` covers `list_runs`, `get_run`, `list_compute_envs`, `get_compute_env`, `list_agents` and `list_site_files` (see the `Caller` docstring).
- No table has an owner. `store.py`: `compute_envs`, `agents` and `launches` have no user column. `confirmations.caller_user_id` already exists. Run rows live in the rebuildable `index.db`, so ownership comes from `platform.db` `launches.run_name`.
- No check uses an owner. `compute_envs.get/list_all`, `jobs._target`, `enqueue_listing` and `enqueue_confirmed` (which writes `launches`), and `build.primary_environment`/`prepare_launch` all ignore one.
- Agents register by their own hello (`agents.register`). Agent tokens carry no user (`cli.py` agent-token new; `store.create_token` allows `user_id` only for `pat`; `lookup_token` returns no user).
- The terminal launch and cancel pass `caller=None` (`abf_launch/cli.py`). This is pinned by AST in `tests/test_pat.py` tcd10.
- 009c already makes `request_cancel` refuse runs the caller did not launch (`confirm.launched_by`), and `find_cancel` is filtered by caller.
- The samplesheet file is confined to `<uploads_root>/<caller name>` (`read_confined_samplesheet`). The path cells inside the sheet are checked only against the environment's roots (`abf_station/launch.py` `inputs_from_environment`).

## Design decisions (developer-agent)
1. **Owner columns.**
   - Add `compute_envs.owner_user_id`, `agents.owner_user_id` and `launches.user_id`. All are INTEGER NULL and added in place (pattern of `_add_agent_columns`).
   - `launches.user_id` goes last. `_LAUNCH_COLUMNS`, the migration and the same-order pins are updated together.
   - NULL means local CLI only.
   - `launches.user_id` is copied from the confirmation's `caller_user_id` inside `enqueue_confirmed`, in the same transaction. The `launch`/`cancel` signatures stay unchanged.
2. **One rule at the storage layer.**
   - `caller=None` means the local terminal or stdio, and it sees everything, as today.
   - With a caller, only that user's rows match.
   - A row owned by another user or by nobody answers exactly like a missing row: the same "not found" words, with no hint that it exists.
3. **Runs.**
   - A run belongs to the caller when the newest `launches` row for its name has `user_id = caller`.
   - `list_runs` filters by the caller's run-name set. `get_run` resolves the name, then checks ownership.
   - Runs with no launches row, or with a NULL user, are hidden over HTTP, MCP-over-HTTP and the web.
4. **Launch and listing check the environment's owner twice.**
   - When building the launch: the primary or only environment is chosen among the caller's own. `set_primary` is per owner.
   - At the queue: `_target` and `enqueue_confirmed` refuse with the not-found words when the confirmation's caller differs from the environment's owner, or from its agent's owner.
   - `ce create`/`update` refuse an agent with a different owner.
5. **Agents.**
   - `abf-platform agent-token new NAME --user USER` stores the user. `create_token` allows `user_id` for `kind="agent"`, and `lookup_token` returns `user_id`.
   - `agents.register` sets the owner from the token. If the row has a different non-NULL owner, hello is refused (403, the same shape as `wrong_name`). A NULL owner is filled by the first owned token.
   - `ce create --owner USER` defaults to the single user when exactly one exists; otherwise the flag is required. `ce update --owner` reassigns.
6. **Cancel.** The 009c owner check stays. The enqueue cancel branch also checks that the confirmation's caller owns the launch row. Terminal cancel (no caller) stays unrestricted and does not name an account (ruling: whoever has the shell can already kill the Slurm job).
7. **Terminal launch names the account (maintainer decision).**
   - `abf-launch ... --user NAME` resolves the user and passes a `Caller`. It is required once any user exists; with no users it is omitted and the row stays NULL. An unknown name is refused before the question.
   - The terminal yes is still typed at a TTY; the `_require_human` gate is untouched.
   - The honest boundary in `docs/PLATFORM.md`: whoever has the shell can name any account.
8. **Sample path cells.**
   - For a caller that is not None, every path cell must lie inside that caller's own area `<uploads_root>/<caller name>`. This is the same real-path area as the samplesheet; factor out one `caller_area()`.
   - The terminal and stdio keep today's roots.
   - The agent re-check is unchanged. A per-user site folder for a remote station is a 009h follow-up.
9. **Listing site files.** For a caller that is not None, a path inside `uploads_root` is allowed only inside the caller's own folder. Other paths follow the existing readRoots rule.
10. **Migration.**
    - `store.assign_orphans`, idempotent, runs at `serve`, `mcp`, `web`, `ce` and launch start.
    - Exactly one user: that user adopts every NULL row. Two or more users: nothing is adopted. Zero users: nothing happens.
    - The meta key `owners_assigned` is written once at least one user exists.
    - `ce list` and `launches` print the owner, or "(none: local only)".
    - `rebuild` still never opens `platform.db` or `tokens.db`.

## Tests (red first; the verifier writes the cases)
- Two users, A and B, over HTTP and MCP:
  - Each sees only their own environments, agents and runs. A get on the other user's names returns the same words as a missing name.
  - B cannot launch on A's environment, list through it, or cancel A's run. A's confirmed cancel is never reused for B.
- A launch by A writes `launches.user_id = A`.
- Terminal launch:
  - `--user A` records A.
  - With no `--user` while users exist, it is refused before the question.
  - With no users, it records NULL.
- NULL-owner rows and runs are invisible over HTTP and visible on stdio and the CLI.
- Sample cells:
  - Cells outside the caller's own area are refused over HTTP, even when they are inside the environment's readRoots.
  - A's area passes for A. B's area is refused for A.
  - The terminal and stdio keep the old roots.
- `list_site_files` into another user's upload folder is refused.
- Agents and environments:
  - An agent token of B cannot take over A's agent.
  - An environment cannot be bound to another owner's agent.
- Migration:
  - One user adopts all orphans. Two users adopt none. Zero users writes no mark.
  - A second start changes nothing. `rebuild` leaves `platform.db` and `tokens.db` alone.
  - A pre-116 `platform.db` upgrades in place and keeps the `launches` column order.
- Pins expected to be rewritten. Each goes in the ledger with the old expectation, the new one and the reason; nothing is deleted or loosened.
  - `test_pat.py`: tcd01 (reads ignore the caller), tcf03_f04, tcb08_b09, tcd10 (terminal `caller=None`), tcd11 (column set), tca12 (the `create_token` rule), tcc05/06 if the `lookup_token` shape is pinned.
  - The `launches` column-order pins in `test_launch_followup.py` and `test_launch_platform.py`.
  - Fixtures that create environments or agents (`make_ce`, `human_harness`) gain an owner. This is a setup change only.
  - The terminal launch tests gain `--user`.
- Unchanged and green: tce04 and tcf09 (signatures), the three channel singletons, the receiver tests, and the agent re-check tests.

## Not in this PR
- Roles or lab-wide sharing (010 postponed).
- Remote-station per-user folders (009h).
- OAuth (009i).
- Any change to who may say yes.

## Constitution Check
- I.2: the confirmation gate is untouched. Ownership narrows what a caller can reach; it is not a confirmation.
- Safety Net: every new check is a refusal. An unknown owner means refuse.
- Governance: tier A, no amendment.
  - Update the `docs/PLATFORM.md` and CHANGELOG lines in this PR.
  - The `no session/cookie/password` schema scan gets no new exception. The column names are `owner_user_id` and `user_id`.
