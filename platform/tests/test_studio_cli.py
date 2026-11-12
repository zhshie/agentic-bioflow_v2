# Nothing existing: no test covers a command that writes files on a user's own computer from what read-only MCP tools answer; the tests of the run page and of the MCP tools stop at the server.
"""cli-fetch-publish-figure, slice 1: the fetch-results command, the R code it prints, and the strings of studio_cli. The answers of the tools are fakes
(studio_harness.FakeSite), no network is used. Test case numbers are in the comments (specs/cli-fetch-publish-figure/test-case.md).
publish-figure is slice 2 and is in test_studio_publish.py (the slice 1 pin TC-053 "nothing of it exists yet" is flipped below)."""
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from studio_harness import FakeSite, patch_session
from test_web_wording_sweep import CJK_RE, banned_in

PKG = PLATFORM_DIR / "abf_platform"
MAX = 26214400


@pytest.fixture(autouse=True)
def _world(tmp_path, monkeypatch):
    for k in list(os.environ):
        if k.startswith("ABF_"):
            monkeypatch.delenv(k)
    monkeypatch.setenv("LC_ALL", "zh_TW.UTF-8")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))      # not the HOME variable: a subprocess would lose the user site-packages
    (tmp_path / "home").mkdir()
    from abf_platform import studio_cli
    monkeypatch.setattr(studio_cli, "POLL_SECONDS", 0.01)
    return tmp_path


def fetch(argv, capsys):
    from abf_platform import cli
    try:
        rc = cli.main(["fetch-results"] + list(argv))
    except SystemExit as e:
        rc = e.code
    out = capsys.readouterr()
    return rc, out.out, out.err


def got(folder):
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


BASE = {"ASV_table.tsv": "id\ts1\ta\t1\n", "counts.tsv": "g\tn\nx\t5\n", "notes.md": "# notes\n", "DATA.TSV": "u\tv\n1\t2\n"}


def test_tc014_the_tables_go_to_one_folder_the_first_line_names_it_and_the_rest_is_skipped(tmp_path, capsys, monkeypatch):
    # TC-014
    files = dict(BASE, **{"report.html": "<html></html>", "x.bam": "BAM\x01"})
    site = FakeSite(files=files)
    patch_session(monkeypatch, site)
    rc, out, err = fetch(["run1"], capsys)
    default = tmp_path / "home" / "abf-results" / "run1"
    assert rc == 0, (out, err)
    assert out.splitlines()[0].endswith(str(default)) and str(default) in out
    assert sorted(got(default)) == ["ASV_table.tsv", "DATA.TSV", "counts.tsv", "notes.md"]
    other = tmp_path / "elsewhere"
    rc, out, err = fetch(["run1", "--dir", str(other)], capsys)
    assert rc == 0 and sorted(got(other)) == sorted(got(default)) and str(other) in out.splitlines()[0]
    # the default folder was not made a second time by --dir: remove it and run with --dir again
    import shutil
    shutil.rmtree(default)
    fetch(["run1", "--dir", str(other)], capsys)
    assert not default.exists()


def test_tc015_depth_three_and_two_hundred_files_and_the_summary_does_not_claim_everything(tmp_path, capsys, monkeypatch):
    # TC-015
    from abf_platform import studio_remote
    files = {"d1/d2/ok.tsv": "a\n", "d1/d2/d3/deep.tsv": "b\n", "top.tsv": "t\n"}
    site = FakeSite(files=files)
    patch_session(monkeypatch, site)
    rc, out, err = fetch(["r1", "--dir", str(tmp_path / "o")], capsys)
    assert sorted(got(tmp_path / "o")) == ["d1/d2/ok.tsv", "top.tsv"], got(tmp_path / "o")
    assert "d1/d2/d3" in out + err and "全部" not in out.replace("並非全部", "") and "並非全部" in out + err and rc == 1
    assert [a.get("path") for a in site.names("run_outputs")] == [None, "d1", "d1/d2"]      # only the paths of enter, level by level
    many = {"t%03d.tsv" % i: "x\n" for i in range(201)}
    site = FakeSite(files=many)
    patch_session(monkeypatch, site)
    rc, out, err = fetch(["r2", "--dir", str(tmp_path / "p")], capsys)
    assert len(got(tmp_path / "p")) == 200 and "t200.tsv" not in got(tmp_path / "p") and "並非全部" in out + err and rc == 1
    assert len(site.names("read_run_file")) == 200


def test_tc016_pages_are_joined_bit_for_bit_with_crlf_and_chinese(tmp_path, capsys, monkeypatch):
    # TC-016
    text = "樣本\tcount\r\n甲\t1\r\n乙\t2\r\n" * 3
    site = FakeSite(files={"a.tsv": text}, page=len(text) // 3 + 1)
    patch_session(monkeypatch, site)
    rc, out, err = fetch(["r1", "--dir", str(tmp_path / "o")], capsys)
    assert rc == 0 and got(tmp_path / "o")["a.tsv"] == text.encode("utf-8")
    offsets = [a.get("offset") for a in site.names("read_run_file")]
    assert len(offsets) == 3 and offsets[0] in (0, None) and offsets == sorted(offsets)


def test_tc017_a_loading_answer_is_asked_again_every_two_seconds(tmp_path, capsys, monkeypatch):
    # TC-017
    from abf_platform import studio_cli
    source = (PKG / "studio_cli.py").read_text(encoding="utf-8")
    assert re.search(r"^POLL_SECONDS = 2(\.0)?\b", source, re.M)
    site = FakeSite(files={"a.tsv": "x\n"}, loading=2)
    patch_session(monkeypatch, site)
    rc, out, err = fetch(["r1", "--dir", str(tmp_path / "o")], capsys)
    assert rc == 0 and got(tmp_path / "o") == {"a.tsv": b"x\n"} and len(site.names("read_run_file")) == 3


def test_tc018_a_listing_or_a_file_that_never_gets_ready_ends_at_the_deadline(tmp_path, capsys, monkeypatch):
    # TC-018
    from abf_platform import studio_cli
    source = (PKG / "studio_cli.py").read_text(encoding="utf-8")
    assert re.search(r"^DEADLINE_SECONDS = 120(\.0)?\b", source, re.M)
    monkeypatch.setattr(studio_cli, "DEADLINE_SECONDS", 0.2)
    site = FakeSite(files={"a.tsv": "x\n", "b.tsv": "y\n"}, forever_loading={"a.tsv"})
    patch_session(monkeypatch, site)
    rc, out, err = fetch(["r1", "--dir", str(tmp_path / "o")], capsys)
    assert rc == 1 and "a.tsv" in out + err and got(tmp_path / "o") == {"b.tsv": b"y\n"}
    site = FakeSite(files={"a.tsv": "x\n"}, outputs={"found": True, "state": "loading", "files": []})
    patch_session(monkeypatch, site)
    rc, out, err = fetch(["r1", "--dir", str(tmp_path / "p")], capsys)
    assert rc == 1 and not (tmp_path / "p").exists()


def test_tc019_binaries_and_html_are_never_fetched_and_each_skip_has_a_reason(tmp_path, capsys, monkeypatch):
    # TC-019
    files = {"x.bam": "1", "y.fastq": "2", "z.gz": "3", "p.png": "4", "report.html": "<html>", "kept.tsv": "k\n", "weird.tsv": "w\n"}
    site = FakeSite(files=files, binary={"weird.tsv"})
    patch_session(monkeypatch, site)
    rc, out, err = fetch(["r1", "--dir", str(tmp_path / "o")], capsys)
    assert rc == 1 and sorted(got(tmp_path / "o")) == ["kept.tsv"]      # R11 (the lead, 2026-11-12): a table the platform calls binary is a problem, exit 1
    asked = [a["path"] for a in site.names("read_run_file")]
    assert sorted(asked) == ["kept.tsv", "weird.tsv"]      # nothing else was read, the html not even to get its address
    lines = {name: [l for l in out.splitlines() if name in l] for name in ("x.bam", "y.fastq", "z.gz", "p.png", "report.html", "weird.tsv")}
    for name, found in lines.items():
        assert found and "略過" in found[0], (name, out)
    assert "瀏覽器" in lines["report.html"][0] and "http" not in out


def test_tc020_a_file_over_the_limit_is_listed_by_name_and_size_and_one_at_the_limit_is_read(tmp_path, capsys, monkeypatch):
    # TC-020
    from abf_platform import jobs, studio_cli
    assert studio_cli.RUN_FILE_MAX_BYTES == jobs.RUN_FILE_MAX_BYTES == MAX
    source = (PKG / "studio_cli.py").read_text(encoding="utf-8")
    assert not re.search(r"26214400|25\s*\*\s*1024|1024\s*\*\s*1024\s*\*\s*25", source)
    site = FakeSite(files={"big.tsv": "b\n", "edge.tsv": "e\n"}, sizes={"big.tsv": MAX + 1, "edge.tsv": MAX})
    patch_session(monkeypatch, site)
    monkeypatch.setattr(studio_cli, "MAX_TOTAL_BYTES", 10 * MAX)
    rc, out, err = fetch(["r1", "--dir", str(tmp_path / "o")], capsys)
    assert [a["path"] for a in site.names("read_run_file")] == ["edge.tsv"] and sorted(got(tmp_path / "o")) == ["edge.tsv"]
    assert "big.tsv" in out and str(MAX + 1) in out.replace(",", "") and rc == 1


def test_tc021_a_refusal_of_the_site_is_shown_as_it_was_given_and_the_rest_is_fetched(tmp_path, capsys, monkeypatch):
    # TC-021
    reason = "站台拒絕讀取 results/secret.tsv：不在允許讀取的資料夾內。"
    site = FakeSite(files={"secret.tsv": "s\n", "ok.tsv": "o\n"}, errors={"secret.tsv": {"found": True, "state": "error", "code": "refused", "reason": reason}})
    patch_session(monkeypatch, site)
    rc, out, err = fetch(["r1", "--dir", str(tmp_path / "o")], capsys)
    assert rc == 1 and reason in out + err and sorted(got(tmp_path / "o")) == ["ok.tsv"]


def test_tc024_the_total_cap_stops_the_run_and_lists_what_was_not_fetched(tmp_path, capsys, monkeypatch):
    # TC-024
    from abf_platform import studio_cli
    monkeypatch.setattr(studio_cli, "MAX_TOTAL_BYTES", 10)
    site = FakeSite(files={"a.tsv": "12345\n", "b.tsv": "12345\n", "c.tsv": "12345\n"})
    patch_session(monkeypatch, site)
    rc, out, err = fetch(["r1", "--dir", str(tmp_path / "o")], capsys)
    assert rc == 1 and sorted(got(tmp_path / "o")) == ["a.tsv"] and got(tmp_path / "o")["a.tsv"] == b"12345\n"
    assert "b.tsv" in out + err and "c.tsv" in out + err
    assert re.search(r"MAX_TOTAL_BYTES\s*=\s*100\s*\*\s*1024\s*\*\s*1024", (PKG / "studio_cli.py").read_text(encoding="utf-8"))


def test_tc025_nothing_is_written_outside_the_folder_and_links_are_not_followed(tmp_path, capsys, monkeypatch):
    # TC-025
    rows = [{"name": n, "type": "file", "size": 2, "modified": "", "enter": None, "download": d, "too_large": False}
            for n, d in (("evil.tsv", "../evil.tsv"), ("b.tsv", "a/../../b.tsv"), ("x.tsv", "/etc/x.tsv"), ("c.tsv", ".hidden/c.tsv"),
                         ("w.tsv", "a\\b.tsv"), ("good.tsv", "good.tsv"), ("lnk.tsv", "lnk.tsv"))]
    answer = {"found": True, "state": "ready", "path": "/f/results", "compute_env": "lab-a", "files": rows, "listed_at": 1, "reason": None, "sub": "",
              "bad_path": False, "max_bytes": MAX, "top": []}
    site = FakeSite(files={"good.tsv": "g\n", "lnk.tsv": "L\n"}, outputs=answer)
    patch_session(monkeypatch, site)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "target.tsv").write_text("keep")
    folder = tmp_path / "o"
    folder.mkdir()
    try:
        os.symlink(outside / "target.tsv", folder / "lnk.tsv")
        linked = True
    except (OSError, NotImplementedError):
        linked = False
    rc, out, err = fetch(["r1", "--dir", str(folder)], capsys)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["home", "o", "outside"]
    assert [p.name for p in outside.iterdir()] == ["target.tsv"] and (outside / "target.tsv").read_text() == "keep"
    asked = [a["path"] for a in site.names("read_run_file")]
    for bad in ("../evil.tsv", "a/../../b.tsv", "/etc/x.tsv", ".hidden/c.tsv", "a\b.tsv"):
        assert bad not in asked
    if linked:      # a link in the folder is left alone and not followed
        assert asked == ["good.tsv"] and sorted(p.name for p in folder.iterdir()) == ["good.tsv", "lnk.tsv"] and (folder / "lnk.tsv").is_symlink()
    else:
        assert asked == ["good.tsv", "lnk.tsv"]
    assert "evil.tsv" in out + err and rc == 1


def test_tc026_an_existing_file_is_replaced_and_it_says_so(tmp_path, capsys, monkeypatch):
    # TC-026
    folder = tmp_path / "o"
    folder.mkdir()
    (folder / "a.tsv").write_text("old")
    patch_session(monkeypatch, FakeSite(files={"a.tsv": "new\n", "b.tsv": "b\n"}))
    rc, out, err = fetch(["r1", "--dir", str(folder)], capsys)
    assert rc == 0 and got(folder) == {"a.tsv": b"new\n", "b.tsv": b"b\n"}
    over = [l for l in out.splitlines() if "已覆蓋" in l]
    assert len(over) == 1 and "a.tsv" in over[0]


def test_tc027_a_failed_page_leaves_the_old_file_and_no_half_file_or_temp_file(tmp_path, capsys, monkeypatch):
    # TC-027
    folder = tmp_path / "o"
    folder.mkdir()
    (folder / "a.tsv").write_text("old")
    patch_session(monkeypatch, FakeSite(files={"a.tsv": "x" * 40 + "\n", "b.tsv": "ok\n"}, page=10, fail_page2={"a.tsv"}))
    rc, out, err = fetch(["r1", "--dir", str(folder)], capsys)
    assert rc == 1 and got(folder) == {"a.tsv": b"old", "b.tsv": b"ok\n"} and "a.tsv" in out + err and "the second page failed" in out + err
    assert sorted(p.name for p in folder.iterdir()) == ["a.tsv", "b.tsv"]


def test_tc028_a_run_that_is_not_found_shows_the_message_unchanged_and_makes_no_folder(tmp_path, capsys, monkeypatch):
    # TC-028
    patch_session(monkeypatch, FakeSite(found=False))
    rc, out, err = fetch(["nope"], capsys)
    assert rc == 1 and (out + err).strip() == FakeSite.NO_RUN
    assert not (tmp_path / "home" / "abf-results").exists()


@pytest.mark.parametrize("answer", [{"found": True, "state": "unavailable", "files": [], "reason": "這次執行沒有結果資料夾的紀錄。"},
                                    {"found": True, "state": "error", "files": [], "reason": "站台沒有回應，請稍後再試。"}])
def test_tc030_an_unavailable_or_failed_listing_shows_its_reason_and_writes_nothing(answer, tmp_path, capsys, monkeypatch):
    # TC-030
    patch_session(monkeypatch, FakeSite(outputs=answer))
    rc, out, err = fetch(["r1"], capsys)
    assert rc == 1 and answer["reason"] in out + err and not (tmp_path / "home" / "abf-results").exists()


def test_tc031_the_summary_counts_what_was_fetched_and_skipped_then_prints_the_r_code(tmp_path, capsys, monkeypatch):
    # TC-031
    patch_session(monkeypatch, FakeSite(files={"ASV_table.tsv": "a\tb\n", "x.bam": "1"}))
    rc, out, err = fetch(["r1", "--dir", str(tmp_path / "o")], capsys)
    assert rc == 0
    assert re.search(r"取到 1 個、略過 1 個", out) and str(tmp_path / "o") in out.split("取到 1 個")[1].splitlines()[0] + out.splitlines()[0]
    assert "read.delim(" in out and out.index("取到 1 個") < out.index("Console") < out.index("read.delim(")
    assert "略過 x.bam" in out


def _choices():
    from abf_platform import cli
    return next(a for a in cli.build_parser()._actions if isinstance(getattr(a, "choices", None), dict)).choices


def test_tc032_the_help_says_what_it_is_and_what_it_is_not_and_has_no_user_option(capsys):
    # TC-032
    rc, out, err = fetch(["--help"], capsys)
    assert rc == 0 and "fetch-records" in out and "--user" not in out and "--dir" in out
    for name in ("studio-connect", "fetch-results"):
        sub = _choices()[name]
        assert sub.allow_abbrev is False
        assert not re.search(r"launch|submit|cancel", sub.format_help(), re.I), name


# ---- US3: the R code ---------------------------------------------------------------------------------------------------------------------

def test_tc033_the_asv_and_counts_tables_get_one_read_line_each_and_the_text_is_fixed():
    # TC-033
    from abf_platform import studio_cli
    a = studio_cli.r_snippet(["ASV_table.tsv", "counts.csv", "notes.md"], "/data/u/abf-results/r1")
    assert a == studio_cli.r_snippet(["ASV_table.tsv", "counts.csv", "notes.md"], "/data/u/abf-results/r1")
    assert 'read.delim(file.path("/data/u/abf-results/r1", "ASV_table.tsv"), check.names = FALSE, row.names = 1)' in a
    assert 'read.csv(file.path("/data/u/abf-results/r1", "counts.csv"), check.names = FALSE, row.names = 1)' in a
    assert a.count("read.") == 2 and "notes.md" not in a
    assert "Console" in a.splitlines()[0]
    assert studio_cli.r_snippet(["feature-table.tsv", "Abundance.tsv"], "/d").count("read.delim(") == 2
    assert studio_cli.r_snippet(["only.md"], "/d") == ""


def test_tc034_without_a_candidate_at_most_five_lines_and_the_rest_is_pointed_to():
    # TC-034
    from abf_platform import studio_cli
    snippet = studio_cli.r_snippet(["t%d.tsv" % i for i in range(7)], "/d")
    assert snippet.count("read.delim(") == 5 and "其餘檔案見資料夾" in snippet
    assert studio_cli.r_snippet(["a.tsv", "b.csv"], "/d").count("read.") == 2 and "其餘檔案見資料夾" not in studio_cli.r_snippet(["a.tsv", "b.csv"], "/d")


def test_tc035_windows_paths_become_forward_slashes_and_quotes_and_backslashes_are_escaped():
    # TC-035
    from abf_platform import studio_cli
    snippet = studio_cli.r_snippet(["ASV_table.tsv", 'a"b counts.tsv', "sub\\x counts.tsv"], "C:\\Users\\a b\\res")
    assert 'file.path("C:/Users/a b/res", "ASV_table.tsv")' in snippet
    assert 'a\\"b counts.tsv' in snippet and "sub\\\\x counts.tsv" in snippet
    assert "C:\\" not in snippet


def test_tc036_the_sentence_before_the_code_is_in_both_languages_and_in_written_chinese():
    # TC-036
    from abf_platform import studio_cli
    zh, en = studio_cli.STRINGS["zh"], studio_cli.STRINGS["en"]
    assert set(zh) == set(en)
    assert "RStudio" in zh["paste"] and "Console" in zh["paste"] and "RStudio" in en["paste"] and "Console" in en["paste"]
    for v in zh.values():
        assert banned_in(v) == [], (v, banned_in(v))
    for v in en.values():
        assert not CJK_RE.search(v), v


def test_tc037_neither_the_code_nor_the_output_has_a_token_a_password_a_host_or_a_site_name(tmp_path, capsys, monkeypatch):
    # TC-037
    from abf_platform import studio_cli
    site = FakeSite(files={"ASV_table.tsv": "a\tb\n", "counts.tsv": "c\n"}, compute_env="nano4-lab")
    patch_session(monkeypatch, site)
    rc, out, err = fetch(["r1", "--dir", str(tmp_path / "o")], capsys)
    text = out + err + studio_cli.r_snippet(["ASV_table.tsv"], "/d")
    for bad in ("token", "password", "platform.example", "nano4", "nchc", "analysis/figures", "ts.net"):
        assert bad not in text.lower(), bad
    source = (PKG / "studio_cli.py").read_text(encoding="utf-8")
    for name in ("analysis/figures",):
        assert name not in source


def test_tc038_no_program_is_started_and_the_source_has_no_such_word(tmp_path, capsys, monkeypatch):
    # TC-038
    source = (PKG / "studio_cli.py").read_text(encoding="utf-8")
    assert not re.search(r"subprocess|Rscript|which R\b|os\.system|Popen", source)

    def boom(*a, **k):
        raise AssertionError("a program was started")
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(os, "system", boom)
    patch_session(monkeypatch, FakeSite(files={"counts.tsv": "c\n"}))
    rc, out, err = fetch(["r1", "--dir", str(tmp_path / "o")], capsys)
    assert rc == 0 and "read.delim(" in out


# ---- the strings and the slice ------------------------------------------------------------------------------------------------------------

def test_tc078_the_strings_have_the_same_keys_in_both_languages():
    # TC-078
    from abf_platform import studio_cli
    zh, en = studio_cli.STRINGS["zh"], studio_cli.STRINGS["en"]
    assert set(zh) == set(en) and zh
    assert all(not CJK_RE.search(v) for v in en.values())
    assert all(banned_in(v) == [] for v in zh.values())


def test_tc053_flipped_by_slice_two_publish_figure_is_now_registered_and_called(capsys):
    # TC-053 held for slice 1 ("no publish-figure yet"); slice 2 flips it, as the plan says (TC-054 and TC-071 take its place; the page half is in test_web_downstream.py)
    commands = set(_choices())
    assert {"studio-connect", "fetch-results", "publish-figure"} <= commands
    text = (PKG / "studio_cli.py").read_text(encoding="utf-8")
    assert "publish_figure" in text and "figures" in text
    assert "publish_figure" not in (PKG / "studio_remote.py").read_text(encoding="utf-8")      # the connection module knows no tool by name except the hint it asks for


def test_tc073_the_pinned_tests_are_still_there_and_the_contract_files_were_not_touched():
    # TC-073 (the full comparison with origin/v3 is the reviewer's)
    tests = PLATFORM_DIR / "tests"
    for fname, names in (("test_web_downstream.py", ["test_strings_table_parity_and_wording", "test_board_touches_are_minimal", "test_wording_in_command_block"]),
                         ("test_cli_contract.py", ["test_every_leaf_is_in_the_matrix"])):
        text = (tests / fname).read_text(encoding="utf-8")
        for n in names:
            assert "def %s(" % n in text, (fname, n)
    git = subprocess.run(["git", "cat-file", "-e", "3d106d5f"], cwd=REPO_ROOT, capture_output=True)
    if git.returncode == 0:
        # the lead appends rulings to plan.md after acceptance (an addition is allowed, a deletion or a changed line is not); the two test files stay as they were
        diff = subprocess.run(["git", "diff", "--stat", "3d106d5f", "HEAD", "--", "specs/cli-fetch-publish-figure/test-case.md",
                               "specs/cli-fetch-publish-figure/test-case-overview.md"], cwd=REPO_ROOT, capture_output=True, text=True)
        assert diff.stdout.strip() == "", diff.stdout
        plan = subprocess.run(["git", "diff", "--numstat", "3d106d5f", "HEAD", "--", "specs/cli-fetch-publish-figure/plan.md"],
                              cwd=REPO_ROOT, capture_output=True, text=True)
        assert all(line.split()[1] == "0" for line in plan.stdout.splitlines()), plan.stdout
