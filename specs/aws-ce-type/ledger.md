# AWS Batch 計算環境類型：能建立、驗證、存放（預檢不花錢） progress ledger

- [x] RED: platform/tests/test_aws_ce.py (57 tests; TC-061, TC-103, TC-104 are manual)
- [x] compute_envs.py: AWS, CHECK_ONLY_TYPES, CHECKABLE, _check_aws, snapshot branch
- [x] abf_station/aws_preflight.py (seven checks) and handlers.py branch
- [x] jobs._target: any job other than the preflight is refused for AWS (aws-launch)
- [x] cli.py: --region, --job-queue, legacy-record check, no "ce update" advice for old records
- [x] existing assertions updated as the plan lists (station_envs, gcb_ce, station_docs, launch_cli)
- [x] docs: PLATFORM.md (AWS Batch section, type table), SEQERA_PARITY.md, TESTING.md
- Note: test_gcb_ce pins the sentence "Slurm and Google Cloud Batch can run; the other types can be modelled only"; PLATFORM.md keeps it and adds the full AWS sentence after it, so that test stays unchanged.
