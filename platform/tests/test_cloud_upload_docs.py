# Nothing existing: the other tests pin CLOUD.md and single keywords of PLATFORM.md; none reads OPERATIONS.md, PLATFORM.md and TESTING.md together for the cloud-upload sentences, the commands they name, or leaked secrets.
"""cloud-upload-docs: the three documents say what the platform does today about files in the lab's bucket.
T1 ... T9 of specs/cloud-upload-docs/plan.md (TC ids in the comments). Only reads text files: no network, no Google account."""
import re

from helpers import PLATFORM_DIR, REPO_ROOT

DOCS = REPO_ROOT / "docs"
OPS = (DOCS / "OPERATIONS.md").read_text(encoding="utf-8")
PLATFORM = (DOCS / "PLATFORM.md").read_text(encoding="utf-8")
TESTING = (DOCS / "TESTING.md").read_text(encoding="utf-8")
CLI = (PLATFORM_DIR / "abf_platform" / "cli.py").read_text(encoding="utf-8")
MCP = (PLATFORM_DIR / "abf_platform" / "mcp_server.py").read_text(encoding="utf-8")
HEAD = "### Datasets in the lab's bucket"


def _section(text, heading):
    start = text.index(heading)
    rest = text[start + len(heading):]
    m = re.search(r"^#{1,3} ", rest, re.M)
    return rest[:m.start()] if m else rest


def test_the_cost_sentence_is_current():
    # TC-010 (T1)
    assert "no cost estimate or cap yet" not in OPS and "docs/CLOUD.md" in OPS


def test_the_new_section_gives_the_place_the_command_and_the_registration():
    # TC-001, TC-002, TC-003, TC-004 (T2)
    assert HEAD in OPS
    sec = _section(OPS, HEAD)
    for word in ("gs://<bucket>/uploads/<user>/", "gcloud storage cp", "rawdata/", "2 GB", "abf-platform dataset register", "--destination"):
        assert word in sec, word
    assert "gsutil" not in sec


def test_the_section_says_who_grants_access_and_what_is_not_wired_yet():
    # TC-006, TC-007 (T3, with the ruling of 2026-10-28: the code exists, no web or AI entry calls it)
    sec = _section(OPS, HEAD)
    assert "does not grant" in sec
    assert "The web page /upload sends files up to 2 GB into the bucket" in sec and "Not built yet" not in sec      # web-upload-page ruling 13


def test_the_section_names_the_launch_argument_and_no_made_up_tool():
    # TC-005 (T4)
    sec = _section(OPS, HEAD)
    tools = set(re.findall(r'server\.tool\(name="([a-z_]+)"', MCP))
    assert "launch" in tools and "`launch`" in sec and "`dataset`" in sec
    for fake in ("register_dataset", "check_web_upload", "get_dataset"):
        assert fake not in sec and fake not in tools


def test_operations_keeps_its_six_headings_and_its_words():
    # TC-001, TC-012 (T5)
    assert len(re.findall(r"^## ", OPS, re.M)) == 6
    for word in ("Java 17", "Nextflow", "gcloud", "storage_root"):
        assert word in OPS, word


def test_platform_input_data_points_at_the_new_section():
    # TC-013, TC-014 (T6)
    assert "Copying files into the bucket is a later feature" not in PLATFORM
    para = next(p for p in PLATFORM.split("\n\n") if p.startswith("**Input data.**"))
    assert "gcloud storage cp" in para and "Datasets in the lab's bucket" in para


def test_testing_steps_use_the_command_not_a_python_shell():
    # TC-020, TC-021 (T7): only the numbered steps, not the introduction
    sec = _section(TESTING, "## Datasets in a cloud bucket (cloud-upload)")
    steps = sec[sec.index("\n1. "):sec.index("**The reviewer.**")]
    assert "Python shell" not in steps and "register_dataset(" not in steps and "check_web_upload(" not in steps
    assert "abf-platform dataset register" in steps
    assert steps.count("Check:") >= 5


def test_every_dataset_command_in_the_documents_exists():
    # TC-004 (T8)
    dataset_group = CLI[CLI.index('da = sub.add_parser("dataset"'):]
    dataset_group = dataset_group[:dataset_group.index("dw.set_defaults")]
    for name, text in (("OPERATIONS", OPS), ("PLATFORM", PLATFORM), ("TESTING", TESTING)):
        for word in re.findall(r"abf-platform dataset ([a-z-]+)", text):
            assert word in {"register", "list", "show"}, (name, word)
    assert '"--destination"' in dataset_group and '"--user"' in dataset_group


def test_no_secret_shapes_in_the_documents():
    # TC-032 (T9)
    for name, text in (("OPERATIONS", OPS), ("PLATFORM", PLATFORM), ("TESTING", TESTING)):
        for mail in re.findall(r"[\w.-]+@[\w.-]*iam\.gserviceaccount\.com", text):
            assert "lab-project-1" in mail, (name, mail)
        assert not re.search(r"abf_pat_[A-Za-z0-9]{8,}", text), name
        assert "BEGIN PRIVATE KEY" not in text, name
