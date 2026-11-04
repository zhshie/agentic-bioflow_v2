# cb-D9 ledger

## RED (unchanged code)

```
        from abf_platform import compute_envs as ce
        msg = ce.credential_findings({"description": "https://user:" + PW + "@h.org/a"}, "x")
>       assert msg and PW not in repr(msg)
E       assert ([])

platform/tests/test_url_credential_patterns.py:74: AssertionError
=========================== short test summary info ============================
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[https://user:hunter2@h.org/a.fq.gz]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[cell3]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[cell4]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[https://h.org/a.fq.gz?X-Amz-Signature=0123456789abcdef0123456789abcdef0123456789abcdef]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[http://u:hunter2@h.org:8080/a.fq.gz]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[ftp://:hunter2@h.org/a.fq.gz]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[https://user:p%40ss@h.org/a.fq.gz]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[https://user:p@ss@h.org/a.fq.gz]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[a sample sheet cell: https://user:hunter2@h.org/a.fq.gz, in the middle of text]
FAILED platform/tests/test_url_credential_patterns.py::test_audit_script_inputs_are_refused_by_the_samplesheet_check[https://user:hunter2@h.org/a.fq.gz]
FAILED platform/tests/test_url_credential_patterns.py::test_audit_script_inputs_are_refused_by_the_samplesheet_check[cell3]
FAILED platform/tests/test_url_credential_patterns.py::test_the_secret_is_not_in_the_refusal
12 failed, 27 passed in 0.12s
```

Note: the AWS audit input is already refused on base (AKIA rule); it passes in RED and stays as a regression case.
