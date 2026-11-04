# Nothing existing: ruling R3 of refusal-visibility (an `error` result is not a refusal; the stored log-in line is checked more tightly).
"""R3: state `error` ("result unknown, may have been submitted") must never say nothing was submitted; open_command allow-list."""
import pytest

from abf_platform import jobs
from test_refusal_visibility import HOST, GOOD, WSL_GOOD, block_of, refused_page, settle, w  # noqa: F401  (w is a fixture)

UNKNOWN = "sbatch 結果不明：可能已送出。"


def test_r3_error_state_zh_does_not_claim_nothing_was_submitted(w):
    # R3-1 (zh)
    ann, rid, job, c = refused_page(w, state="error", message=UNKNOWN, open_command=None)
    page = c.get("/c/" + rid).text
    blk = block_of(page)
    assert blk and "可能已經送出" in blk and "查看站台上的資料夾與 Slurm 工作" in blk
    assert "沒有送出" not in page and "已送出。工作編號" not in page


def test_r3_error_state_en_does_not_claim_nothing_was_submitted(w):
    # R3-1 (en)
    ann, rid, job, c = refused_page(w, state="error", message=UNKNOWN, open_command=None)
    page = c.get("/c/" + rid + "?lang=en").text
    blk = block_of(page)
    assert blk and "may already have been submitted" in blk
    assert "nothing was submitted" not in page


def test_r3_error_state_shows_left_on_site(w):
    # R3-1: the site's own message and left_on_site follow the sentence
    ann, rid, job, c = refused_page(w, state="error", raw={"ok": False, "message": "Head failed.", "left_on_site": "/data/work/run-1"})
    blk = block_of(c.get("/c/" + rid).text)
    assert "Head failed." in blk and "/data/work/run-1" in blk


def test_r3_refused_state_is_unchanged(w):
    # R3-2: refused keeps its words
    ann, rid, job, c = refused_page(w, message="預檢未通過，沒有建立任何東西：java")
    page = c.get("/c/" + rid).text
    assert "站台拒絕了送出，工作沒有送出" in page and "可能已經送出" not in page


@pytest.mark.parametrize("bad", [
    "ssh -o A=b>~/.bashrc u@" + HOST + " true",
    "ssh -o ControlPath=a<b u@" + HOST + " true",
    "ssh -o ControlPath=(x) u@" + HOST + " true",
    "ssh -o ControlPath='x' u@" + HOST + " true",
    'ssh -o ControlPath="x" u@' + HOST + " true",
    "ssh -o ControlPath=a\b u@" + HOST + " true",
    "ssh -o ProxyCommand=foo u@" + HOST + " true",
    "ssh -o LocalCommand=foo u@" + HOST + " true",
    "ssh -o PermitLocalCommand=yes u@" + HOST + " true",
    "ssh -o SomethingElse=1 u@" + HOST + " true",
])
def test_r3_open_command_allow_list_rejects(bad):
    # R3-3
    assert jobs.valid_open_command(bad, HOST) is None


@pytest.mark.parametrize("good", [GOOD, WSL_GOOD,
                                  "ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=yes -o IdentityFile=~/.ssh/id -o Port=22 -o User=u u@" + HOST + " true"])
def test_r3_open_command_allow_list_accepts(good):
    # R3-3
    assert jobs.valid_open_command(good, HOST) == good
