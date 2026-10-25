# releases.repo_of 拒絕「.」段與結尾換行 progress ledger

- [x] repo_of: `_REPO` ends with `\Z`; any `.`/`..` path segment rejected; 6 new reject cases + `a.b/c.d` accept (platform/abf_platform/releases.py, platform/tests/test_releases.py)
