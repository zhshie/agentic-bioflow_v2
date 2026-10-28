# AWS Batch：從平台送出、追蹤、取消一個 run（自動測試；真實試跑等他點頭） progress ledger

- [x] Gate table per environment type (`compute_envs.CLOUD_JOB_KINDS`), `PLATFORM_HOST_TYPES=(GCB, AWS)`, `CHECK_ONLY_TYPES=()`; cloud_store stays Google-only.
- [x] AWS bundle (`launch.render_aws_bundle`: five files, `aws.config`, `head.sh`), shared with the agent's rebuild check.
- [x] Station agent `abf_station/aws_launch.py` (launch after the yes; cancel through the shared `gcb_launch._cancel_head`).
- [x] Screens and terminal wording (billing sentence first, no amounts; cancel note about the AWS Console); resume/relaunch refused.
- [x] Tests `platform/tests/test_aws_launch.py` (69); existing tests updated only as plan A9 lists (test_gcb_ce, test_aws_ce, test_launch_bundle).
- [x] Docs: PLATFORM.md, SEQERA_PARITY.md, OPERATIONS.md, TESTING.md (manual steps 1-7 = TC-171..178, not run).
- [ ] Manual real trial run (TC-171..178): waits for the maintainer's go-ahead.
