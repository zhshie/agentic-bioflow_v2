# k8s-kubeconfig-paste-rule 平台端拒收貼進文字欄位的 kubeconfig 密鑰行 progress ledger

- [x] GREEN: one `re.compile` appended to `_VALUE_PATTERNS` (compute_envs.py); `test_model_key_refusal.py` tc015 `got[6:]` list got the new pattern appended (ruling 6, pin of 5 became 6, nothing else touched); `docs/TESTING.md` step 6 sentence updated (ruling 3).
- RED (before the code change, same commit base): `test_k8s_paste_rule.py` 20 failed / 79 passed (refuse cases red, controls green); after: test_k8s_paste_rule + test_model_key_refusal + test_k8s_ce 99 passed.
- origin/v3 comparison: the 20 red cases above are the only reds on the unchanged code; control cases green. Branch: all three files green.
- grep (ruling 2): the three key names appear only in docs/TESTING.md, specs/k8s-ce/ and this task's specs/test file; no existing test or sample data uses them.
- Old records are not rescanned and there is no migration: an existing record whose description already holds such lines is refused only when `update` re-validates it.
- `git diff --stat`: only compute_envs.py (+1 line), test_model_key_refusal.py (tc015 list), docs/TESTING.md, new test file.

## TC-028 兩分支比對（developer-agent 補跑，2026-10-29 21:2x）
- origin/v3@108bfdff（git archive 快照）：`ABF_PYTEST_TARGETS=tests/test_k8s_ce.py bash tests/platform_test.sh` → `platform tests: pytest exit 0, 0 skipped`
- 本分支 718f43d6：同指令 → `platform tests: pytest exit 0, 0 skipped`
