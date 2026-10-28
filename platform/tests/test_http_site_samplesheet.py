# Nothing existing: tests of http-launch-site-samplesheet (a samplesheet cell may name a file on the site over HTTP, and `launch` takes the CSV itself as samplesheet_text); the rule is ours.
"""http-launch-site-samplesheet: over HTTP a path cell of the samplesheet is judged as a path in `params` is (116b): inside the upload area it must
be a file of the caller's own folder, anywhere else it must lie in the environment's read roots; and `samplesheet_text` gives the CSV without a file.
Test cases are named in the comments (TC-001 ...), see specs/http-launch-site-samplesheet/test-case.md."""
import asyncio
import hashlib
import json
import logging
import os
import re
import sqlite3

import pytest

from helpers import PLATFORM_DIR
from human_harness import PASSWORD, World, csrf_of, form_answer, pending_id_of
from owner_harness import Duo, SHARED, sql_exec, sql_rows
from resume_harness import SESSION

ROOT = PLATFORM_DIR.parent
MIB = 1048576
BOTH_OR_NONE = "samplesheet 與 samplesheet_text 只能給一個"
COLS = ["forwardReads"]


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def counts(d):
    return (len(d.w.jobs()), len(d.w.confirmations()), len(sql_rows(d.state, "SELECT * FROM launches")))


def csv_text(cells, header="sampleID,forwardReads"):
    return header + "\n" + "".join("s%02d,%s\n" % (i, c) for i, c in enumerate(cells, 1))


def site_cells(n=10, root=SHARED):
    return ["%s/microbiome_test/rawdata/Day5_%02d.fastq.gz" % (root, i) for i in range(1, n + 1)]


def by_text(d, who, cells, run="run-one", answer=None, **kw):
    """The AI sends the CSV itself (no file), with the column that holds the paths named."""
    raw = {"path_columns": COLS}
    raw.update(kw.pop("raw", {}))
    return d.launch(who, run=run, answer=answer, text=csv_text(cells), raw_args=raw, **kw)


def refused(out):
    return out["ok"] is False and out["sent"] is False and "job_id" not in out


def pending(out):
    return out["ok"] is True and out["state"] == "pending" and out["sent"] is False


def bundle_of(d, index=0):
    return json.loads(d.w.confirmations()[index]["bundle_json"])


def tree(root):
    """Every file and folder below root, as names (the database's own journal files come and go and are not counted)."""
    out = set()
    for dirpath, dirs, files in os.walk(str(root)):
        for n in dirs + files:
            if not n.endswith(("-wal", "-shm", "-journal")):
                out.add(os.path.relpath(os.path.join(dirpath, n), str(root)))
    return out


# ---- US1: a site file can be sent from Claude ----------------------------------------------------------------------------

def test_tc001_the_lab_case_goes_to_pending_with_samplesheet_text(d):
    # TC-001
    out = by_text(d, d.a, site_cells(10))
    assert pending(out), out
    assert out["confirmation_url"] and "cannot read the samplesheet" not in out["message"] and "自己的上傳資料夾" not in out["message"]


def test_tc002_a_samplesheet_file_in_my_folder_may_name_site_files(d):
    # TC-002 (the old TC-049 turned round)
    out = d.launch(d.a, cells=["%s/x.fq" % SHARED, "%s/y.fq" % SHARED])
    assert pending(out), out


def test_tc003_the_screen_lists_the_pipeline_the_revision_and_the_ten_rows(d):
    # TC-003
    out = by_text(d, d.a, site_cells(10))
    s = out["summary"]
    assert "nf-core/ampliseq" in s and "2.18.0" in s
    for i in range(1, 11):
        assert "microbiome_test/rawdata/Day5_%02d.fastq.gz" % i in s, i


def test_tc004_no_file_is_written_on_the_platform(d):
    # TC-004
    before = tree(d.state.parent)
    assert pending(by_text(d, d.a, site_cells(3)))
    assert refused(by_text(d, d.a, ["/elsewhere/x.fq"], run="run-two"))
    assert tree(d.state.parent) == before


def test_tc005_half_in_my_folder_half_on_the_site_passes(d):
    # TC-005
    area = d.area(d.a)
    out = by_text(d, d.a, ["%s/rawdata/s01.fq" % area, "%s/rawdata/s02.fq" % area, "%s/x.fq" % SHARED, "%s/y.fq" % SHARED])
    assert pending(out), out


def test_tc006_only_my_folder_cells_are_recorded_as_upload_paths(d):
    # TC-006
    area = d.area(d.a)
    mine = ["%s/rawdata/s01.fq" % area, "%s/rawdata/s02.fq" % area]
    assert pending(by_text(d, d.a, mine + ["%s/x.fq" % SHARED]))
    rec = bundle_of(d)["upload_paths"]
    assert rec["area"] == os.path.realpath(str(area))
    assert [e["given"] for e in rec["paths"]] == mine
    assert all(e["real"] == os.path.realpath(e["given"]) for e in rec["paths"])
    assert not any(SHARED in e["given"] for e in rec["paths"])


def test_tc007_the_person_says_yes_and_one_job_exists(d):
    # TC-007
    out = by_text(d, d.a, site_cells(10), answer=form_answer())
    assert out["sent"] is True and out["job_id"], out
    assert len(d.w.jobs("launch_nextflow")) == 1
    assert len(bundle_of(d)["samplesheet"]) - 1 == 10


def test_tc008_the_same_text_and_arguments_find_the_same_job(d):
    # TC-008
    first = by_text(d, d.a, site_cells(4), answer=form_answer())
    again = by_text(d, d.a, site_cells(4))
    assert again["sent"] is True and again["job_id"] == first["job_id"] and again["id"] == first["id"]
    assert len(d.w.jobs("launch_nextflow")) == 1 and len(d.w.confirmations()) == 1


def test_tc009_a_changed_cell_is_not_the_approved_one(d):
    # TC-009
    first = by_text(d, d.a, site_cells(4), answer=form_answer())
    cells = site_cells(4)
    cells[2] = cells[2].replace("Day5_03", "Day5_99")
    other = by_text(d, d.a, cells)                  # the name is taken by the approved launch: nothing is sent, and nothing is the approved job
    assert other["sent"] is False and other.get("job_id") != first["job_id"] and "job_id" not in other
    renamed = d.launch(d.a, text=csv_text(site_cells(4)).replace("s01", "z01"), raw_args={"path_columns": COLS})
    assert renamed["sent"] is False and "job_id" not in renamed
    assert len(d.w.jobs("launch_nextflow")) == 1
    # and where the first one was only asked for, a changed cell or sample name is a different request of its own
    p1 = by_text(d, d.a, site_cells(4), run="run-two")
    p2 = by_text(d, d.a, cells, run="run-two")
    p3 = d.launch(d.a, run="run-two", text=csv_text(site_cells(4)).replace("s01", "z01"), raw_args={"path_columns": COLS})
    assert pending(p1) and pending(p2) and pending(p3) and len({p1["id"], p2["id"], p3["id"]}) == 3


def _fail_run(d, run, job_id, slurm):
    from abf_platform import store
    sql_exec(d.state, "UPDATE jobs SET state = 'done', result_json = ? WHERE id = ?", (json.dumps({"ok": True, "slurm_job_id": slurm}), job_id))
    sql_exec(d.state, "UPDATE launches SET slurm_job_id = ?, submitted_at = confirmed_at WHERE run_name = ?", (slurm, run))
    con = store.connect_index(d.w.ip.index)
    try:
        with con:
            con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at) "
                        "VALUES (?, ?, ?, 'live', 'failed', 1, 2, 3)", ("id-" + run, SESSION, run))
    finally:
        con.close()


def test_tc010_resume_and_relaunch_of_a_site_file_run_are_not_refused(d):
    # TC-010
    a = by_text(d, d.a, site_cells(3), run="run-one", answer=form_answer())
    b = by_text(d, d.a, site_cells(3), run="run-two", answer=form_answer())
    assert a["sent"] and b["sent"]
    _fail_run(d, "run-one", a["job_id"], 4101)
    _fail_run(d, "run-two", b["job_id"], 4102)
    resumed = d.call("resume", {"run_name": "run-one"}, caller=d.a)
    assert pending(resumed), resumed
    relaunched = d.call("relaunch", {"run_name": "run-two"}, caller=d.a)
    assert pending(relaunched), relaunched


# ---- US2: shapes that must still be refused ------------------------------------------------------------------------------

def _roots_cover_uploads(d):
    d.sheet(d.b)                     # B's folder exists
    (d.area(d.b) / "y.fq").write_text("x")
    return d.uploads


def test_tc011_a_cell_in_bobs_folder_written_through_a_read_root_is_refused(d):
    # TC-011
    _roots_cover_uploads(d)
    out = by_text(d, d.a, ["%s/y.fq" % d.area(d.b)])
    assert refused(out) and counts(d) == (0, 0, 0)


def test_tc012_the_same_by_a_samplesheet_file(d):
    # TC-012
    _roots_cover_uploads(d)
    out = d.launch(d.a, cells=["%s/y.fq" % d.area(d.b)])
    assert refused(out) and counts(d) == (0, 0, 0)


def test_tc013_a_link_in_the_shared_folder_leading_into_bobs_folder_is_refused(d, tmp_path):
    # TC-013
    _roots_cover_uploads(d)
    shared = tmp_path / "shared"
    shared.mkdir()
    os.symlink(str(d.area(d.b)), str(shared / "link"))
    rc, msg = d.w.ip.run("ce", "update", "lab-a", "--read-root=%s" % d.uploads, "--read-root=%s" % SHARED, "--read-root=%s" % shared)
    assert rc == 0, msg
    out = by_text(d, d.a, ["%s/link/y.fq" % shared])
    assert refused(out) and counts(d) == (0, 0, 0)


def test_tc014_a_link_in_my_own_folder_leading_into_bobs_folder_is_refused(d):
    # TC-014
    _roots_cover_uploads(d)
    d.area(d.a).mkdir(parents=True, exist_ok=True)
    os.symlink(str(d.area(d.b)), str(d.area(d.a) / "link"))
    out = by_text(d, d.a, ["%s/link/y.fq" % d.area(d.a)])
    assert refused(out) and counts(d) == (0, 0, 0)


def test_tc015_dot_dot_is_refused_in_both_directions(d):
    # TC-015
    _roots_cover_uploads(d)
    name = d.uploads.name
    for cell in ("%s/../%s/%s/y.fq" % (SHARED, name, d.b.name), "%s/%s/../%s/y.fq" % (d.uploads, d.a.name, d.b.name)):
        out = by_text(d, d.a, [cell])
        assert refused(out), cell
    assert counts(d) == (0, 0, 0)


def test_tc016_irregular_spellings_of_bobs_file_are_refused(d):
    # TC-016
    _roots_cover_uploads(d)
    u, b = str(d.uploads), d.b.name
    for cell in ("%s//%s/./y.fq" % (u, b), "%s/%s//y.fq" % (u, b), "%s/%s/y.fq/" % (u, b), "%s/./%s/y.fq" % (u, b), "%s//%s/y.fq" % (u, b)):
        assert refused(by_text(d, d.a, [cell])), cell
    assert counts(d) == (0, 0, 0)


def test_tc017_the_upload_root_and_a_folder_itself_are_not_files_of_mine(d):
    # TC-017
    _roots_cover_uploads(d)
    d.area(d.a).mkdir(parents=True, exist_ok=True)
    for cell in (str(d.uploads), str(d.area(d.b)), str(d.area(d.a))):
        assert refused(by_text(d, d.a, [cell])), cell
    assert counts(d) == (0, 0, 0)


def test_tc018_a_neighbour_folder_that_starts_with_my_name_is_not_mine(d):
    # TC-018
    neighbour = d.uploads / (d.a.name + "x")
    neighbour.mkdir(parents=True)
    (neighbour / "z.fq").write_text("x")
    out = by_text(d, d.a, ["%s/z.fq" % neighbour])
    assert refused(out) and counts(d) == (0, 0, 0)


def test_tc019_a_cell_outside_every_read_root_is_refused_with_the_read_root_words(d):
    # TC-019
    for cell in ("/etc/passwd", "/elsewhere/x.fq"):
        out = by_text(d, d.a, [cell])
        assert refused(out) and re.search(r"read roots|允許讀取的範圍之外|允許範圍之外", out["message"]), out
    assert counts(d) == (0, 0, 0)


def test_tc020_the_same_by_a_samplesheet_file(d):
    # TC-020
    out = d.launch(d.a, cells=["/elsewhere/x.fq", "/elsewhere/y.fq"])
    assert refused(out) and re.search(r"read roots|允許讀取的範圍之外|允許範圍之外", out["message"]), out
    assert counts(d) == (0, 0, 0)


def test_tc021_a_relative_cell_is_refused(d):
    # TC-021
    out = by_text(d, d.a, ["rawdata/x.fq"])
    assert refused(out) and counts(d) == (0, 0, 0)


def test_tc022_one_bad_cell_refuses_the_whole_launch(d):
    # TC-022
    _roots_cover_uploads(d)
    cells = site_cells(9) + ["%s/y.fq" % d.area(d.b)]
    out = by_text(d, d.a, cells)
    assert refused(out) and counts(d) == (0, 0, 0)


def test_tc023_the_refusal_does_not_tell_about_bob(d):
    # TC-023
    _roots_cover_uploads(d)
    given = "%s/y.fq" % d.area(d.b)
    out = by_text(d, d.a, [given])
    msg = out["message"]
    assert os.path.realpath(str(d.area(d.a))) in msg
    assert "bob" not in msg and "y.fq" not in msg and given not in msg


def test_tc024_the_samplesheet_file_itself_must_still_be_in_my_folder(d):
    # TC-024
    b_sheet = d.sheet(d.b, ["%s/x.fq" % SHARED])
    d.area(d.a).mkdir(parents=True, exist_ok=True)
    os.symlink(str(b_sheet), str(d.area(d.a) / "link.csv"))
    for path in (SHARED + "/sheet.csv", str(b_sheet), "%s/%s/../%s/%s" % (d.uploads, d.a.name, d.b.name, b_sheet.name), str(d.area(d.a) / "link.csv")):
        out = d.launch(d.a, sheet=path)
        assert refused(out) and re.search(r"samplesheet 必須是你自己上傳資料夾裡的檔案|讀不到，或不是你自己上傳資料夾裡的一般檔案", out["message"]), (path, out)
    assert counts(d) == (0, 0, 0)


# ---- US3: the samplesheet_text argument ----------------------------------------------------------------------------------

def test_tc025_both_given_is_refused(d):
    # TC-025
    sheet = d.sheet(d.a, ["%s/x.fq" % SHARED])
    out = d.launch(d.a, text=csv_text(site_cells(2)), raw_args={"samplesheet": str(sheet), "path_columns": COLS})
    assert refused(out) and BOTH_OR_NONE in out["message"] and counts(d) == (0, 0, 0)


def test_tc026_neither_given_is_refused(d):
    # TC-026
    out = d.launch(d.a, nosheet=True)
    assert refused(out) and BOTH_OR_NONE in out["message"] and counts(d) == (0, 0, 0)


def test_tc027_an_empty_text_is_not_content(d):
    # TC-027
    out = d.launch(d.a, text="")
    assert refused(out) and "samplesheet_text" in out["message"] and "Traceback" not in out["message"] and counts(d) == (0, 0, 0)


def test_tc028_one_byte_over_a_mebibyte_is_refused(d):
    # TC-028
    out = d.launch(d.a, text="a" * (MIB + 1))
    assert refused(out) and "1 MiB" in out["message"] and "太大" in out["message"] and counts(d) == (0, 0, 0)
    two_byte = "é" * (MIB // 2) + "a"          # 1 MiB + 1 in UTF-8 bytes, fewer characters
    assert len(two_byte) <= MIB and len(two_byte.encode("utf-8")) == MIB + 1
    assert "太大" in d.launch(d.a, text=two_byte)["message"]


def test_tc029_exactly_a_mebibyte_is_not_refused_for_its_size(d):
    # TC-029
    out = d.launch(d.a, text="a" * MIB)
    assert refused(out) and "太大" not in out["message"] and "too large" not in out["message"], out


def test_tc030_a_nul_is_refused(d):
    # TC-030
    out = d.launch(d.a, text="sampleID,forwardReads\ns01,/data/shared/a\x00b.fq\n")
    assert refused(out) and "NUL" in out["message"] and counts(d) == (0, 0, 0)


def test_tc031_text_that_is_not_text_is_refused_plainly(d):
    # TC-031
    from abf_platform import actions
    for bad in (123, ["a,b"], {"a": 1}, b"a,b", True):
        out = asyncio.run(actions.request_launch(d.state, pipeline="nf-core/ampliseq", revision="2.18.0", run_name="run-x", samplesheet=None,
                                                 samplesheet_text=bad, ce_name="lab-a", caller=d.a))
        assert refused(out) and "CSV" in out["message"] and "Traceback" not in out["message"], (bad, out)
    assert counts(d) == (0, 0, 0)


def test_tc032_bad_csv_is_refused_in_the_words_of_the_file_route(d):
    # TC-032
    for body in ("sampleID,forwardReads\n", "sampleID,forwardReads\ns01,/data/shared/a.fq\ns02\n", "sampleID,forwardReads\ns01,/data/shared/a.fq,extra\n"):
        sheet = d.area(d.a) / "bad.csv"
        d.area(d.a).mkdir(parents=True, exist_ok=True)
        sheet.write_text(body, encoding="utf-8")
        by_file = d.launch(d.a, sheet=sheet, raw_args={"path_columns": COLS})
        by_text_out = d.launch(d.a, text=body, raw_args={"path_columns": COLS})
        assert refused(by_file) and refused(by_text_out)
        assert by_file["message"] == by_text_out["message"], (body, by_file, by_text_out)
    assert counts(d) == (0, 0, 0)


def test_tc033_the_same_csv_by_file_and_by_text_gives_the_same_bundle_and_screen(d):
    # TC-033
    cells = ["%s/x.fq" % SHARED, "%s/y.fq" % SHARED]
    sheet = d.sheet(d.a, cells)
    text = sheet.read_text(encoding="utf-8")
    f = d.launch(d.a, run="run-fff", sheet=sheet)
    t = d.launch(d.a, run="run-ttt", text=text)
    assert pending(f) and pending(t)
    bf, bt = (json.dumps(bundle_of(d, i), sort_keys=True).replace(n, "RUN") for i, n in ((0, "run-fff"), (1, "run-ttt")))
    assert bf == bt
    assert f["summary"].replace("run-fff", "RUN") == t["summary"].replace("run-ttt", "RUN")


def test_tc034_stdio_takes_samplesheet_text(d):
    # TC-034
    out = by_text(d, None, site_cells(3), answer=form_answer())
    assert out["sent"] is True and out["job_id"], out
    assert "upload_paths" not in bundle_of(d)
    outside = by_text(d, None, ["/elsewhere/x.fq"], run="run-two", answer=form_answer())
    assert refused(outside)       # the read roots still hold for stdio


def test_tc035_stdio_without_a_form_is_still_refused(d):
    # TC-035
    out = by_text(d, None, site_cells(3))
    assert refused(out) and "終端機" in out["message"] and counts(d) == (0, 0, 0)


# ---- US4: rules that were not loosened -----------------------------------------------------------------------------------

def test_tc038_a_params_path_into_bobs_folder_still_refuses_good_cells(d):
    # TC-038
    _roots_cover_uploads(d)
    out = by_text(d, d.a, site_cells(2), raw={"params": {"primer": "AGRG", "extra": "%s/a.fq" % d.area(d.b)}})
    assert refused(out) and re.search(r"params extra", out["message"]) and "bob" not in out["message"] and counts(d) == (0, 0, 0)


def test_tc040_the_terminal_and_stdio_refuse_a_cell_outside_the_read_roots_as_before(d):
    # TC-040
    from abf_launch import build
    sheet = d.sheet(d.a, ["/elsewhere/x.fq", "/elsewhere/y.fq"])
    with pytest.raises(build.Refusal) as e:
        build.prepare_launch(d.state, ce="lab-a", pipeline="nf-core/ampliseq", revision="2.18.0", run_name="run-t", samplesheet=str(sheet))
    assert re.search(r"read roots|允許讀取的範圍之外|允許範圍之外", str(e.value))
    out = d.launch(None, answer=form_answer(), sheet=sheet)
    assert refused(out) and re.search(r"read roots|允許讀取的範圍之外|允許範圍之外", out["message"])


def test_tc044_somebody_elses_environment_is_not_found_by_text(d):
    # TC-044
    d.bobs_environment()
    other = by_text(d, d.a, site_cells(2), ce_name="b1")
    missing = by_text(d, d.a, site_cells(2), ce_name="nonesuch")
    assert refused(other) and other["message"].replace("b1", "<n>") == missing["message"].replace("nonesuch", "<n>")
    assert counts(d) == (0, 0, 0)


def test_tc045_an_environment_nobody_owns_is_not_usable_by_text(d):
    # TC-045
    d.an_environment_nobody_owns()
    assert refused(by_text(d, d.a, site_cells(2), ce_name="e0")) and counts(d) == (0, 0, 0)


# ---- US5: the human gate and the other person ----------------------------------------------------------------------------

def test_tc047_without_a_form_the_answer_is_a_pending_request_and_no_job(d):
    # TC-047
    out = by_text(d, d.a, site_cells(2))
    assert pending(out) and "再呼叫" in out["message"]
    assert counts(d) == (0, 1, 0)
    assert sql_rows(d.state, "SELECT * FROM jobs WHERE kind = 'launch_nextflow'") == []


def test_tc048_no_argument_can_say_yes(d):
    # TC-048
    tools, _ = d.w.mcp([])
    props = {t.name: set(t.input_schema["properties"]) for t in tools}["launch"]
    assert "samplesheet_text" in props
    assert not any(re.search(r"confirm|approve|yes|send|force|skip|accept|送出", p, re.I) for p in props), props


def test_tc049_bob_cannot_press_alices_request(d, w):
    # TC-049
    out = by_text(d, d.a, site_cells(2))
    rid = pending_id_of(out["confirmation_url"])
    client = w.web()
    assert w.login(client, "bob").status_code == 303
    page = client.get("/c/" + rid)
    posted = client.post("/c/" + rid, data={"csrf": csrf_of(page.text) or "x"})
    assert posted.status_code == 403
    assert sql_rows(d.state, "SELECT state FROM confirmations WHERE id = ?", (rid,))[0]["state"] == "pending"
    assert counts(d)[0] == 0


def test_tc050_bob_sees_nothing_of_alices_request(d, w):
    # TC-050
    out = by_text(d, d.a, site_cells(2))
    rid = pending_id_of(out["confirmation_url"])
    client = w.web()
    assert w.login(client, "bob").status_code == 303
    page = client.get("/c/" + rid)
    assert page.status_code == 403
    for word in ("Day5_01", "microbiome_test", "run-one", "nf-core/ampliseq"):
        assert word not in page.text


def test_tc051_the_same_text_from_bob_is_bobs_own_new_request(d):
    # TC-051
    d.bobs_environment()
    a = by_text(d, d.a, site_cells(2), answer=form_answer())
    b_on_hers = by_text(d, d.b, site_cells(2), run="run-b", ce_name="lab-a")
    assert refused(b_on_hers)
    b = by_text(d, d.b, site_cells(2), run="run-b", ce_name="b1")
    assert pending(b) and b["id"] != a["id"] and "job_id" not in b
    assert len(d.w.jobs("launch_nextflow")) == 1


def test_tc052_the_refusals_say_what_and_what_to_do_and_hide_the_platform(d):
    # TC-052
    _roots_cover_uploads(d)
    sheet = d.sheet(d.a, ["%s/x.fq" % SHARED])
    outs = [by_text(d, d.a, ["%s/y.fq" % d.area(d.b)]), by_text(d, d.a, ["/elsewhere/x.fq"]),
            d.launch(d.a, text=csv_text(site_cells(1)), raw_args={"samplesheet": str(sheet)}), d.launch(d.a, text="a" * (MIB + 1)),
            d.launch(d.a, text="a\x00b")]
    area = os.path.realpath(str(d.area(d.a)))
    for out in outs:
        assert refused(out), out
        msg = out["message"].replace(area, "<A>")
        for bad in ("Traceback", "SELECT", "sqlite", ".py", str(d.state.parent), "File \""):
            assert bad not in msg, (bad, msg)
        assert len(msg) > 15


def test_tc053_no_secret_is_in_the_answers_or_the_log(d, caplog, capfd):
    # TC-053
    caplog.set_level(logging.DEBUG)
    outs = [by_text(d, d.a, site_cells(2)), by_text(d, d.a, ["/elsewhere/x.fq"], run="run-two")]
    seen = json.dumps(outs, ensure_ascii=False) + caplog.text + capfd.readouterr().out + capfd.readouterr().err
    assert PASSWORD not in seen and not re.search(r"abf_[A-Za-z0-9_-]{16,}", seen) and "Bearer" not in seen


# ---- US6: documents, old pins, no new schema -----------------------------------------------------------------------------

def test_tc054_the_document_says_the_three_places_and_why():
    # TC-054
    doc = (ROOT / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    assert doc.count("samplesheet_text") >= 3
    assert "Over HTTP every path cell of the samplesheet must lie" not in doc
    assert re.search(r"remote (station|site)[^.]*(no|has no|without)[^.]*(folder|per-user)", doc, re.I) or "每人" in doc
    assert re.search(r"read roots", doc) and "uploads_root" in doc


def test_tc055_the_ledger_lists_each_rewritten_pin():
    # TC-055
    ledger = (ROOT / "specs" / "http-launch-site-samplesheet" / "ledger.md").read_text(encoding="utf-8")
    for pin in ("test_tc049_a_cell_inside_the_read_roots", "TC-LS-52"):
        assert pin in ledger, pin
    assert "2026-10-23" in ledger
    assert ledger.lower().count("old") >= 2 and ledger.lower().count("new") >= 2


SCHEMA_SHA256 = "d39c4e436fb4c9250331453cf454d52b25c60528cf67079ce362d22432939f33"      # release-lookup-job: the jobs CHECK list gained pipeline_files (was bb8b185e8eef...); byte-channel-a: gained put_upload (was 0b6aad18e811...)


def test_tc057_no_table_or_column_changed(d):
    # TC-057
    con = sqlite3.connect(str(d.state))
    try:
        rows = con.execute("SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name").fetchall()
    finally:
        con.close()
    assert hashlib.sha256(json.dumps(rows).encode("utf-8")).hexdigest() == SCHEMA_SHA256


# ---- out of scope --------------------------------------------------------------------------------------------------------

def test_tc058_tc059_tc060_no_upload_tool_no_site_job_no_folder_job(d):
    # TC-058, TC-059, TC-060
    tools, _ = d.w.mcp([])
    assert {t.name for t in tools} == {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files",
                                       "list_used_pipelines", "read_task_log", "run_outputs", "my_usage", "launch", "cancel", "forget", "resume", "relaunch"}
    before = tree(d.uploads)
    jobs_before = [r["id"] for r in sql_rows(d.state, "SELECT id FROM jobs")]
    assert pending(by_text(d, d.a, site_cells(3)))
    assert tree(d.uploads) == before
    assert [r["id"] for r in sql_rows(d.state, "SELECT id FROM jobs")] == jobs_before      # not a read, a list or a mkdir for the site, before the person says yes


def test_tc061_the_same_lab_shares_nothing_by_text(d):
    # TC-061
    a = by_text(d, d.a, site_cells(2), answer=form_answer())
    b = by_text(d, d.b, site_cells(2), ce_name="lab-a", answer=form_answer())
    assert refused(b)
    assert len(d.w.jobs("launch_nextflow")) == 1 and a["sent"] is True


# ---- the safety net ------------------------------------------------------------------------------------------------------

def test_cs01_three_calls_without_a_yes_queue_nothing(d):
    # CS-01
    for _ in range(3):
        out = by_text(d, d.a, site_cells(3))
        assert out["sent"] is False
    assert d.w.jobs() == [] and sql_rows(d.state, "SELECT * FROM launches") == []


def test_cs02_the_web_form_asks_first_and_takes_site_cells(d, w):
    # CS-02
    d.sheet(d.a, ["%s/x.fq" % SHARED, "%s/y.fq" % SHARED], name="web.csv")
    client = w.web()
    assert w.login(client, "alice").status_code == 303
    page = client.get("/launch").text
    assert "samplesheet_text" not in page
    csrf = re.search(r'<form class="lform"[^>]*><input type="hidden" name="csrf" value="([^"]+)"', page).group(1)
    import html
    sheet = html.unescape(re.search(r'<select name="samplesheet"[^>]*>.*?<option value="([^"]+)"', page, re.S).group(1))
    r = client.post("/launch", data={"csrf": csrf, "pipeline": "nf-core/ampliseq", "revision": "2.18.0", "run_name": "web-run",
                                     "samplesheet": sheet, "ce_name": "lab-a", "params": "",
                                     "shown_pipeline": "nf-core/ampliseq", "shown_revision": "2.18.0"})      # guided-launch-2b
    assert r.status_code == 303 and re.fullmatch(r"/c/[0-9a-f]{32}", r.headers["location"]), r.text
    assert d.w.jobs() == [] and len(d.w.confirmations()) == 1


SHAPES = [("bob via read root", lambda d: "%s/y.fq" % d.area(d.b)), ("upload root itself", lambda d: str(d.uploads)),
          ("bob folder itself", lambda d: str(d.area(d.b))), ("dotdot out of shared", lambda d: "%s/../%s/%s/y.fq" % (SHARED, d.uploads.name, d.b.name)),
          ("dotdot inside mine", lambda d: "%s/%s/../%s/y.fq" % (d.uploads, d.a.name, d.b.name)),
          ("double slash", lambda d: "%s//%s/y.fq" % (d.uploads, d.b.name)), ("dot segment", lambda d: "%s/./%s/y.fq" % (d.uploads, d.b.name)),
          ("neighbour prefix", lambda d: "%s/%sx/z.fq" % (d.uploads, d.a.name)), ("etc", lambda d: "/etc/passwd"),
          ("relative", lambda d: "rawdata/x.fq"), ("home", lambda d: "~/x.fq")]


@pytest.mark.parametrize("label", [s[0] for s in SHAPES])
def test_cs03_every_shape_the_base_refused_is_still_refused_and_the_one_allowed_shape_passes(d, label):
    # CS-03
    _roots_cover_uploads(d)
    (d.uploads / (d.a.name + "x")).mkdir(exist_ok=True)
    cell = dict(SHAPES)[label](d)
    by_path = d.launch(d.a, cells=[cell])
    by_content = by_text(d, d.a, [cell])
    assert refused(by_path) and refused(by_content), (label, by_path, by_content)
    for out in (by_path, by_content):
        assert "bob" not in out["message"] and "y.fq" not in out["message"]
    assert counts(d) == (0, 0, 0)
    assert pending(by_text(d, d.a, ["%s/x.fq" % SHARED]))       # the one shape the maintainer allowed
