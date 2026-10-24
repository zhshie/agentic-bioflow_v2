# 挑選 nf-core 最新正式版本的邏輯（不連網） progress ledger

## Red run (before releases.py existed)

`pytest platform/tests/test_releases.py` -> `ImportError: cannot import name 'releases' from 'abf_platform'` (collection error, so T1-T22 all fail because the module does not exist).
