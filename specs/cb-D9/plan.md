# cb-D9 plan: URL credential patterns

Source: cloud-burn tasks.json D9. Branch fix/cb-d9-url-credential-patterns, base origin/v3 (375bfde7).

## Goal
`compute_envs.looks_like_credential` must refuse a URL that carries its secret in userinfo
(`https://user:pw@host/...`) or in a pre-signed query (`X-Goog-Signature=`, `X-Amz-Signature=`).
The four inputs of `docs/reports/audit-2026-11/03_web_cell_credential_gate.py` are accepted today by
`abf_station.launch._check_samplesheet`, which relies on this heuristic for http(s) cells.
(The AWS input is already refused on base, by the AKIA rule; kept as a regression case.)

## Files
- `platform/abf_platform/compute_envs.py` (rules only)
- `platform/tests/test_url_credential_patterns.py` (new)

## Approach
Two new regexes: userinfo `scheme://[^\s/?#@]*:[^\s/?#@]*@`-shaped (userinfo ends at the first `/ ? #`,
so '@' in a path, query or fragment does not match; a name with no password does not match) and
`[?&](X-Amz-Signature|X-Goog-Signature)=<16+ chars>` (case-insensitive).

## RED tests
Audit inputs (userinfo, X-Goog-Signature) plus neighbouring shapes; counter-examples that must still pass.

## Done criteria
New file green, RED output in ledger, old shapes identical on base and branch (corpus compare),
run_all green, scope guard OK.

## Environment facts
Existing tests `test_model_key_refusal.py::test_tc015` and `test_k8s_paste_rule.py` pin the exact content
of `_VALUE_PATTERNS` and cannot be edited here (outside allowed files). See ledger for how this is handled.

## Not doing
No change to abf_station, to the samplesheet check, to other pattern lists, or to any existing test.
