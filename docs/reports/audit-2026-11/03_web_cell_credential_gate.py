"""PR #301 (platform/abf_station/launch.py:_check_samplesheet): an http(s) samplesheet cell skips path checks and is refused only if
compute_envs.looks_like_credential(cell). Fact the safety rests on: that heuristic catches the usual ways a URL carries a secret.
Refute with userinfo and pre-signed URLs.
Run: python3 -I docs/reports/audit-2026-11/03_web_cell_credential_gate.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "platform"))
from abf_station import launch

cells = [
 "https://h.org/a.fq.gz?token=abc123",                                    # control: refused
 "https://user:hunter2@h.org/a.fq.gz",                                    # userinfo
 "https://b.s3.amazonaws.com/a.fq.gz?X-Amz-Credential=" + "AKIA" + "IOSFODNN7EXAMPLE%2F20261101%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
 "https://storage.googleapis.com/b/a.fq.gz?X-Goog-Signature=0123456789abcdef0123456789abcdef0123456789abcdef",
]
for cell in cells:
    try:
        launch._check_samplesheet([["sample", "fastq_1"], ["s1", cell]], [], ["/work"])
        print("ACCEPTED  %s" % cell[:70])
    except launch.BundleError:
        print("refused   %s" % cell[:70])
