# Kubernetes 計算環境可以送出分析（head 以 Pod 在叢集內跑、bundle 走 Secret） progress ledger

Run stamp 20261029-2255-L40c. Branch feat/k8s-launch.

## Done

- [x] Gate tables (`compute_envs.py`): `K8S` moved into `PLATFORM_HOST_TYPES`, `CHECK_ONLY_TYPES == ()`, `CLOUD_JOB_KINDS[K8S]` = preflight, launch_nextflow, cancel_run, pipeline_files.
- [x] `jobs.py`: Kubernetes refuses clean_work, put_upload, list_site_files, fetch_run_records, read_task_log in plain words (尚未支援).
- [x] `abf_station/launch.py`: Kubernetes bundle (`render_k8s_bundle`), `_snapshot_ce` branch, resume refusal.
- [x] `abf_station/k8s_launch.py` (new): Secret + head Pod via `kubectl create -f -` (stdin); cancel deletes only the head Pod; `cancel.py` and `fetch.py` wired.
- [x] `abf_launch/build.py`, `cli.py`: launch and cancel screens, started line, cancel for a run with no head Pod refused.
- [x] Docs: PLATFORM.md, SEQERA_PARITY.md, TESTING.md (manual steps), OPERATIONS.md (head image, kubeconfig, RBAC).

No migration needed: no table, column or configuration key changes. `result.slurm_job_id` is the fixed placeholder 1; `pod_name` lives in the bundle.

## Existing assertions changed (ruling 12-2: value swaps only)

- test_k8s_ce: `PLATFORM_HOST_TYPES == (3 types)` -> `(3 types, "k8s-platform")`; `CHECK_ONLY_TYPES == ("k8s-platform",)` -> `()`; `CLOUD_JOB_KINDS` K8S absent -> 4 kinds.
- test_k8s_ce job refusals: launch_nextflow refused -> passes `check_target`; messages "尚未支援送出"/"k8s-launch" -> "Kubernetes"/"尚未支援" (clean_work, put_upload, list_site_files, enqueue_listing).
- test_k8s_ce docs: row `checked on the platform host (launch: not yet)` -> `checked and launched on the platform host (upload, clean, resume: not yet)`; SEQERA row `Have (create + check); launch not yet` -> `Have (create + check + launch + cancel; resume not yet)`; pre-flight tail `the read-only checks (create + check; launch not yet)` -> `them (create + check + launch + cancel; resume not yet)`.
- test_aws_ce, test_gcb_ce, test_azure_ce, test_aws_launch, test_azure_launch: `PLATFORM_HOST_TYPES` + `"k8s-platform"`; `CHECK_ONLY_TYPES == ("k8s-platform",)` -> `()`.
- test_aws_ce, test_gcb_ce, test_azure_ce, test_azure_launch, test_azure_upload, test_gcb_launch: sentence `... Azure Batch can run; Kubernetes can be created and checked on the platform host (launch: not yet); the other nine ...` -> `... Azure Batch and Kubernetes can run; the other nine ...`.

## Deviations and notes

- Ruling 12-3 says `launch._snapshot_ce` already had a K8s base branch; it did not, so one was added. TC-077 (identical to base) holds for `compute_envs.snapshot`; `maxMemoryGB` is not added for K8s.
- `site.run_fixed` gained an optional `stdin` argument (manifests go through stdin). `site.py` is not in the plan's file list.
- `abf_launch/cli.py` (fix round, TC-112/TC-113): the Kubernetes words are in every place the command line speaks of a number: the "已啟動" line is exactly `已啟動：Pod <名>（命名空間 <ns>）；叢集的運算費用從現在開始計` (no billing sentence after it; the billing sentence stays as the first paragraph of the launch screen, TC-105), the "未送出" line says 「Pod 名稱」 (platform found with `build.is_k8s` on the row's environment), the "結果不明" line and the `launches` list say Pod, and a cancel prints the agent's own message. The other types print what they printed.
- The agent's "已啟動" message is the same exact line; the not-found cancel says 「Pod 已不存在，視為已停止」 (TC-129); the cancel reminder says the system deletes only the head Pod, the task pods are the person's to clear, and the cost runs until they stop (TC-132).
- Fix round tests added in `test_k8s_launch.py`: TC-113 (equality), TC-118/119 (cancel screen, no job before the yes), TC-120/121, TC-128 (cut at 200), TC-127 (unconfirmed cancel), TC-133/134/135 (second user), TC-136/137 (platform side), TC-112 (cli), TC-163..TC-166 and TC-168/172/174/178/180 (docs). The `# TC-nnn` comments of the cancel tests were renumbered to the contract's ids.
- Docs: `docs/PLATFORM.md` "Launching on Kubernetes" now says ReadWriteMany and the Role the service account needs (not created here); `docs/TESTING.md` steps now cover RWX/RBAC/image, answer n then y with no Pod before the y, the task-pod verdict recorded in this ledger, and that the steps are class C, need the maintainer, and are outside the definition of done.
- Task pods after a real cancel (TC-178): not run here (needs a real cluster, class C); to be filled in by the maintainer after the manual run.

## BLOCKED (one question)

`platform/tests/test_settings_pick_installed.py:844` (`test_the_pinned_cloud_types`) asserts `tuple(web_settings.CLOUD_TYPES) == tuple(compute_envs.PLATFORM_HOST_TYPES) == CLOUD_PLATFORMS` (the three Batch types). Ruling 12-2 puts K8S into `PLATFORM_HOST_TYPES`, so it fails. The plan forbids editing `web_settings.py` and does not list this test. Proposed fix: compare against `PLATFORM_HOST_TYPES` minus K8S, or add K8S to `web_settings.CLOUD_TYPES` and `CLOUD_PLATFORMS`. Left unmodified.

## Ruling 12-11 (resolves the BLOCKED above)

- test_settings_pick_installed `test_the_pinned_cloud_types`: `... == tuple(compute_envs.PLATFORM_HOST_TYPES) == CLOUD_PLATFORMS` -> `... == tuple(t for t in compute_envs.PLATFORM_HOST_TYPES if t != compute_envs.K8S) == CLOUD_PLATFORMS` (value swap; web_settings.py untouched).
- Out-of-scope changes ratified: `site.run_fixed` stdin, `launch._snapshot_ce` K8s branch, `cli.py` started line.

## Fix round (verifier: TC-078, TC-065)

- [x] `k8s_launch._check_tools`: the three refusals (missing, not a regular file, permissions too open) no longer name the kubeconfig path; they say "憑證檔" and point at the environment variable `ABF_STATION_KUBECONFIG` (same approach as the Azure `[credential file]`).
- [x] `k8s_launch._text` takes the kubeconfig path and replaces it with `[credential file]`; every kubectl output / preflight detail shown goes through it.
- [x] Tests: `test_messages_never_name_the_credential_file_or_code` (TC-078: all credential refusals, launch and cancel, plus kubectl errors that echo the path; no path, no Traceback, no code dir); TC-065 loop now includes the missing-file failure path.

## Fix round 2 (verifier: TC-160, TC-126, TC-061, TC-073, TC-068, TC-077, TC-148, and the mislabelled TC-060/TC-053/TC-128)

### Ruling 12-12, TC-126 guarantee 1 (namespace of a cancel comes from the record kept at launch)

It did not hold: `build.prepare_cancel` took the namespace from `bundle_mod.snapshot_ce(view)`, the environment as it is now. Fixed (only the way the cancel bundle is built):
- `platform/abf_launch/build.py` `_launched_ce` (new, the old `_launched_workdir` now calls it) reads the environment snapshot stored with the launch (`jobs.launch_content`: the confirmation's bundle, or the launch job's bundle).
- `platform/abf_launch/build.py` `prepare_cancel`, in the `if view["platform"] == bundle_mod.K8S:` branch (about line 327-334): `bundle["ce"]["namespace"]` is set from that stored snapshot; if the record is gone (run forgotten, confirmation and job cleared) the cancel is refused in plain words and names the Pod to look for. Context and every other field still come from the environment.
- Test: `test_the_cancel_namespace_is_the_one_stored_when_the_run_was_sent` (TC-126): launch, then change the environment's namespace, then `prepare_cancel` gives the namespace of the launch. Red first (933f4068), green 2fa3986a.
- Guarantee 2 (the confirmation screen shows the namespace) is `test_the_cancel_screen_of_a_started_k8s_run_and_the_yes_before_any_job` (NS in the screen) and `test_prepare_launch_screen_and_cancel_for_kubernetes` (NS in the launch screen).

### Tests that now check what their TC says (all in `platform/tests/test_k8s_launch.py`, new block at the end)

- TC-060, TC-061: `test_a_failed_pod_log_tail_loses_the_token_and_the_kubeconfig_and_is_cut_at_200` (log with the run token, the fake kubeconfig text and then 600 characters; no token, no kubeconfig token, no kubeconfig path in the answer; a 600-character tail shows at most 200 characters). This passed without a code change: `_text` already cuts at 200 and `_scrub` removes the secrets.
- TC-073: `test_a_unique_params_value_is_only_in_the_secrets_base64` (`ZZ-UNIQUE-PARAM-VALUE` is in the Secret's base64 `params.yaml` only; not in the Pod manifest, the Secret manifest text, argv, stdin, or the answer). Passed without a code change.
- TC-068: `test_every_kubectl_call_names_the_context_and_never_switches_it` covers every call of a launch, a cancel and a failed launch (reads included). One call is exempt: `kubectl config get-contexts -o name` (the preflight's "does the context exist" check from the k8s-ce task) lists the contexts of the file and has no context to name; `k8s_preflight.py` is not in this task's file list and was not changed. The verifier should rule if TC-068 means that call too.
- TC-077: `test_snapshot_ce_of_a_k8s_environment_is_the_platform_snapshot_without_a_memory_cap`: `compute_envs.snapshot` of a K8s environment keeps its nine keys; `launch.snapshot_ce` equals it on all of them and adds only environment/nextflowConfig/preRunScript/postRunScript; no `maxMemoryGB` even if the view has one. Note (as in "Deviations" above): the base (49d763dd) `launch._snapshot_ce` had no K8s branch (a K8s view fell through to the Slurm shape), so "identical to base" can only hold for `compute_envs.snapshot` and for the four other types' branches, which are untouched.
- TC-148: `test_the_files_of_a_k8s_bundle_are_none_of_them_run_records` (`launch.K8S_SECRET_KEYS` and `K8S_FILE_NAMES` are subsets of `fetch._NOT_RECORDS`).
- TC-053: `test_checkable_types_are_the_same_ones_as_before_with_k8s_once` (K8S once, no duplicates, `CHECKABLE == (SUPPORTED, GCB, AWS, AZURE, K8S)`, the same members in the same order as before).
- TC-128: the length assertion in `test_cancel_failure_is_reported_once_and_cut_at_200` is now `== 200` (was `150 <= n <= 200`) for a stderr of more than 600 characters.

### TC-160: the other four types, v3 base against this branch (same test command at both commits)

Command at each commit: `abf-fast-suite <worktree> --pytest tests/<file>.py` (base = 49d763dd, the v3 commit this branch was made from, in a temporary detached worktree that was removed afterwards; branch = 2fa3986a).

| test file (types it covers) | base 49d763dd | branch 2fa3986a |
|---|---|---|
| test_gcb_launch.py (Google Batch) | 75 passed | 75 passed |
| test_aws_launch.py (AWS Batch) | 105 passed | 105 passed |
| test_azure_launch.py (Azure Batch) | 74 passed | 74 passed |
| test_station_launch.py (Slurm and the agent launch path) | 64 passed | 64 passed |
| test_station_cancel.py (Slurm and the cloud cancel path) | 70 passed | 70 passed |
| test_launch_bundle.py (bundles of every type) | 233 passed | 233 passed |
| test_launch_platform.py (the platform side of launch) | 30 passed | 30 passed |
| test_launch_cli.py (command line of launch/cancel) | 72 passed | 72 passed |

The tests of GCB/AWS/Azure that were edited on this branch (the pinned sentence, `PLATFORM_HOST_TYPES`, `CHECK_ONLY_TYPES`, listed under "Existing assertions changed") are the only differences between the two runs' test files; the counts are equal.
