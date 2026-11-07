# gitleaks-classify progress ledger

Status: BLOCKED (executor may not write `.github/workflows/security.yml`). Developer-agent must apply the edit below.

## Done
- [x] RED 677ca26f: 7 new checks (+ PR-scan-no-report check) in `tests/ci_security_workflow_test.sh`, added to the final loop; existing 12 untouched. Against current security.yml: 3 FAIL (scan flags, upload block, sha-pinned upload) as expected.
- [x] `docs/TESTING.md`: new subsection "Gitleaks report artifact" after the CI security checks section (add only).
- [x] Verified the new tests pass (all 20 ok) against a temp copy of security.yml with the edit below.

## Developer-agent: apply to `.github/workflows/security.yml` (gitleaks job only)
Replace the "Scan full history" step's run line and add the upload step right after it:

```yaml
      - name: Scan full history
        run: gitleaks git --redact --no-banner --config .gitleaks.toml --report-format json --report-path gitleaks-report.json
      - uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02  # v4.6.2
        if: always()
        with:
          name: gitleaks-report
          path: gitleaks-report.json
          if-no-files-found: ignore
          retention-days: 14
```
Then run `bash tests/ci_security_workflow_test.sh` (expect all ok) and the full suite.

## SHA lookup (TC-019)
`gh api repos/actions/upload-artifact/releases` newest v4: v4.6.2. `gh api repos/actions/upload-artifact/git/ref/tags/v4.6.2` -> object.type `commit`, sha `ea165f8d65b6e75b540449e92b4886f43607fa02` (lightweight tag, no further resolve).

## Not done
- Fake-key experiment (TC-017/018): gitleaks 8.30.1 downloaded, sha256 matched the workflow's pinned value, but the WSL run was held by Blast Radius (no answer) twice. Developer-agent must do it (steps in TESTING.md).
- Full suite not run: HEAD cannot be green until security.yml is edited.

## Blast radius (draft, to confirm after the edit)
- Capability added: upload one artifact; permissions unchanged (top-level `contents: read` only, no job `permissions:`).
- Fork exposure: trigger stays `pull_request`; no `secrets.` reference; no `pull_request_target`.
- Report redaction: pending TC-017 experiment. Report holds Author/Email (personal data); artifact readable only by people with repo read access; email is already in public git log if the repo is public.
- Required checks: `tests.yml`, `.gitleaks.toml`, pip-audit job untouched.
- Removal: delete the upload step and the two appended flags, or revert the commit.

## Developer-agent follow-up (2026-11-07)
- Applied the `security.yml` edit above verbatim (gitleaks job only; `git diff --stat`: 8 insertions, 1 deletion). upload-artifact SHA re-verified by lead: `gh api repos/actions/upload-artifact/git/ref/tags/v4.6.2` -> commit `ea165f8d65b6e75b540449e92b4886f43607fa02`.
- `bash tests/ci_security_workflow_test.sh` (WSL): all 20 ok, "all ci_security_workflow checks passed".
- **TC-017/018 fake-key experiment (done, WSL, gitleaks 8.30.1, sha256 verified):** temp repo with fake `AKIA…` + secret-key line, `--redact --report-format json`: 2 findings (`aws-access-token`, `generic-api-key`), `Secret` = `REDACTED`, `Match` = `REDACTED` / `aws_secret_access_key = REDACTED`; raw-key occurrences in report = 0.
- Blast radius confirmed: only new capability is uploading one redacted artifact; top-level `permissions: contents: read` unchanged; no `secrets.`; trigger stays `pull_request`; tests.yml / .gitleaks.toml / pip-audit untouched. Report contains Author/Email (readable only with repo read access).
