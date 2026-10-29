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
