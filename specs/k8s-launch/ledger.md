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
- `abf_launch/cli.py`: only the "submitted" line got Kubernetes wording; `_not_submitted_lines` and `cmd_launches` still print "Slurm 工作編號" because the row there carries no platform information.

## BLOCKED (one question)

`platform/tests/test_settings_pick_installed.py:844` (`test_the_pinned_cloud_types`) asserts `tuple(web_settings.CLOUD_TYPES) == tuple(compute_envs.PLATFORM_HOST_TYPES) == CLOUD_PLATFORMS` (the three Batch types). Ruling 12-2 puts K8S into `PLATFORM_HOST_TYPES`, so it fails. The plan forbids editing `web_settings.py` and does not list this test. Proposed fix: compare against `PLATFORM_HOST_TYPES` minus K8S, or add K8S to `web_settings.CLOUD_TYPES` and `CLOUD_PLATFORMS`. Left unmodified.

## Ruling 12-11 (resolves the BLOCKED above)

- test_settings_pick_installed `test_the_pinned_cloud_types`: `... == tuple(compute_envs.PLATFORM_HOST_TYPES) == CLOUD_PLATFORMS` -> `... == tuple(t for t in compute_envs.PLATFORM_HOST_TYPES if t != compute_envs.K8S) == CLOUD_PLATFORMS` (value swap; web_settings.py untouched).
- Out-of-scope changes ratified: `site.run_fixed` stdin, `launch._snapshot_ce` K8s branch, `cli.py` started line.
