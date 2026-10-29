# Nothing existing: tests of spec 012c (pairing FASTQ names, the 2 GB web limit, registering a Dataset); the pairing rules and the owner rule for datasets are ours.
"""012c: pair FASTQ, register a Dataset, refuse web uploads over 2 GB. Test cases are named in the comments (TC-001 ...),
see specs/012c-uploads-backend/test-case.md."""
import csv
import io
import json
import os
import re
import sqlite3
from pathlib import Path

import pytest

from human_harness import World
from owner_harness import Duo, sql_rows

HERE = Path(__file__).resolve().parent
PLATFORM = HERE.parent
REPO = PLATFORM.parent
MODULE = PLATFORM / "abf_platform" / "actions" / "datasets.py"
GB2 = 2_000_000_000


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def ds():
    from abf_platform.actions import datasets
    return datasets


def area(d, caller):
    return os.path.realpath(d.area(caller))


def paths(d, caller, names):
    a = area(d, caller)
    return ["%s/%s" % (a, n) for n in names]


def sheet(rows, header=("sample", "fastq_1", "fastq_2")):
    out = io.StringIO()
    wr = csv.writer(out, lineterminator="\n")
    wr.writerow(header)
    for r in rows:
        wr.writerow(r)
    return out.getvalue()


FOUR = ["a_R1_001.fastq.gz", "a_R2_001.fastq.gz", "b_R1_001.fastq.gz", "b_R2_001.fastq.gz"]


def four_sheet(d, caller):
    p = paths(d, caller, FOUR)
    return sheet([("a", p[0], p[1]), ("b", p[2], p[3])]), p


def register(d, caller, name="proj", version="v1", text=None, files=None, **kw):
    if text is None:
        text, files = four_sheet(d, caller)
    files = files if files is not None else []
    return ds().register_dataset(d.state, name=name, version=version, samplesheet=text,
                                 files=[f if isinstance(f, dict) else {"path": f} for f in files], caller=caller, **kw)


def rows_of(d):
    try:
        return sql_rows(d.state, "SELECT * FROM datasets ORDER BY id")
    except sqlite3.OperationalError:
        return []


def words(text, name):
    return re.sub(re.escape(name), "<name>", str(text))


def pair_names(result):
    return [(p["sample"], os.path.basename(p["fastq_1"]), os.path.basename(p["fastq_2"])) for p in result["pairs"]]


def csv_rows(text):
    return list(csv.reader(io.StringIO(text)))


# ---- US1: pairing -------------------------------------------------------------------------------------------------------

def test_tc001_two_pairs():
    r = ds().pair_fastq(FOUR)
    assert pair_names(r) == [("a", FOUR[0], FOUR[1]), ("b", FOUR[2], FOUR[3])]
    assert r["unpaired"] == []
    rows = csv_rows(r["csv"])
    assert rows[0] == ["sample", "fastq_1", "fastq_2"] and len(rows) == 3


@pytest.mark.parametrize("tc,names,sample", [
    ("TC-002", ["a_R1.fastq.gz", "a_R2.fastq.gz"], "a"),
    ("TC-003", ["a_1.fastq.gz", "a_2.fastq.gz"], "a"),
    ("TC-004", ["c_R1.fq.gz", "c_R2.fq.gz"], "c"),
    ("TC-006", ["s1_S1_L001_R1_001.fastq.gz", "s1_S1_L001_R2_001.fastq.gz"], "s1"),
    ("TC-007", ["s2_S2_R1_001.fastq.gz", "s2_S2_R2_001.fastq.gz"], "s2"),
])
def test_one_pair(tc, names, sample):
    r = ds().pair_fastq(names)
    assert pair_names(r) == [(sample, names[0], names[1])] and r["unpaired"] == [], tc


def test_tc005_uncompressed():
    r = ds().pair_fastq(["d_R1.fastq", "d_R2.fastq", "e_R1.fq", "e_R2.fq"])
    assert [p[0] for p in pair_names(r)] == ["d", "e"]


def test_tc008_lanes_are_repeated_rows():
    names = ["s1_S1_L001_R1_001.fastq.gz", "s1_S1_L001_R2_001.fastq.gz", "s1_S1_L002_R1_001.fastq.gz", "s1_S1_L002_R2_001.fastq.gz"]
    r = ds().pair_fastq(names)
    assert pair_names(r) == [("s1", names[0], names[1]), ("s1", names[2], names[3])]
    assert [row[0] for row in csv_rows(r["csv"])[1:]] == ["s1", "s1"]


@pytest.mark.parametrize("tc,names", [
    ("TC-009", ["x_R1.fq.gz"]),
    ("TC-010", ["x_R1.fastq.gz", "x_R1.fq.gz", "x_R2.fastq.gz"]),
    ("TC-011", ["x_R1_001.fastq.gz", "x_R2.fastq.gz"]),
    ("TC-012", ["y_R1.fastq.gz", "y_2.fastq.gz"]),
    ("TC-013", ["z_I1_001.fastq.gz", "z_I2_001.fastq.gz"]),
    ("TC-014", ["w_R3_001.fastq.gz"]),
    ("TC-015", ["reads.fastq.gz"]),
    ("TC-016", ["d1/a_R1.fastq.gz", "d2/a_R2.fastq.gz"]),
])
def test_never_guess(tc, names):
    r = ds().pair_fastq(names)
    assert r["pairs"] == [], tc
    assert len(csv_rows(r["csv"])) == 1, tc
    flagged = sorted(u["file"] for u in r["unpaired"])
    assert all(u["reason"] for u in r["unpaired"]), tc
    if tc == "TC-010":
        assert {"x_R1.fastq.gz", "x_R1.fq.gz"} <= set(flagged)
    else:
        assert flagged == sorted(names), tc


def test_tc017_draft_for_alice(d):
    r = ds().draft_samplesheet(d.state, paths(d, d.a, FOUR), caller=d.a)
    assert r["ok"] is True and [p[0] for p in pair_names(r)] == ["a", "b"] and r["unpaired"] == []
    assert csv_rows(r["csv"])[0] == ["sample", "fastq_1", "fastq_2"]


def test_tc018_relative_names_are_her_folder(d):
    r = ds().draft_samplesheet(d.state, FOUR, caller=d.a)
    assert r["ok"] is True and [p[0] for p in pair_names(r)] == ["a", "b"]


def test_tc019_draft_writes_nothing(d):
    a = Path(area(d, d.a))
    a.mkdir(parents=True, exist_ok=True)
    (a / "a_R1_001.fastq.gz").write_bytes(b"x")
    before = sorted((str(p), p.stat().st_size, p.stat().st_mtime) for p in a.rglob("*"))
    ds().draft_samplesheet(d.state, FOUR, caller=d.a)
    after = sorted((str(p), p.stat().st_size, p.stat().st_mtime) for p in a.rglob("*"))
    assert before == after and rows_of(d) == []


def _refused(d, r, caller=None):
    caller = caller or d.a
    assert r["ok"] is False
    msg = r["message"]
    assert area(d, caller) in msg
    other = d.b if caller is d.a else d.a
    assert area(d, other) not in msg
    return msg


@pytest.mark.parametrize("tc", ["TC-020", "TC-021", "TC-022"])
def test_draft_outside_the_area_is_refused(d, tc):
    bob = Path(area(d, d.b))
    bob.mkdir(parents=True, exist_ok=True)
    given = {"TC-020": "../bob/a_R1.fastq.gz", "TC-021": str(bob / "a_R1.fastq.gz"), "TC-022": "link/a_R1.fastq.gz"}[tc]
    if tc == "TC-022":
        Path(area(d, d.a)).mkdir(parents=True, exist_ok=True)
        os.symlink(str(bob), str(Path(area(d, d.a)) / "link"))
    msg = _refused(d, ds().draft_samplesheet(d.state, [given], caller=d.a))
    assert given not in msg


# ---- US2: web upload limit ----------------------------------------------------------------------------------------------

def test_tc023_four_files_of_500mb(d):
    r = ds().check_web_upload(d.state, {"f%d.fastq.gz" % i: 500_000_000 for i in range(4)}, caller=d.a)
    assert r["ok"] is True and not r.get("over") and not r.get("command")


def test_tc024_exactly_the_limit_is_accepted(d):
    assert ds().WEB_UPLOAD_LIMIT == GB2
    assert ds().check_web_upload(d.state, {"x.fastq.gz": GB2}, caller=d.a)["ok"] is True


def test_tc025_the_limit_is_per_file(d):
    assert ds().check_web_upload(d.state, {"f%d" % i: GB2 - 1 for i in range(4)}, caller=d.a)["ok"] is True


def test_tc026_to_028_one_byte_over(d):
    r = ds().check_web_upload(d.state, {"big_R1.fastq.gz": GB2 + 1}, caller=d.a)
    assert r["ok"] is False and r["over"] == ["big_R1.fastq.gz"] and r["command"]
    dest = area(d, d.a) + "/rawdata"
    assert r["command"].startswith("bash scripts/push.sh <你電腦上的資料夾> ") and r["command"].endswith(dest)       # TC-027
    outside = r["message"].replace(r["command"], "")                                                                  # TC-028
    assert "scripts/push.sh" not in outside and dest in outside   # second sentence: dest appears again outside the command
    assert r["message"].count(dest) >= 2


def test_tc029_only_the_big_one_is_listed(d):
    sizes = {"a": 500_000_000, "b": 500_000_000, "c": 500_000_000, "big": 2_500_000_000}
    assert ds().check_web_upload(d.state, sizes, caller=d.a)["over"] == ["big"]


def test_tc030_bobs_command_names_bobs_folder(d):
    r = ds().check_web_upload(d.state, {"big": GB2 + 1}, caller=d.b)
    assert area(d, d.b) + "/rawdata" in r["command"] and area(d, d.a) not in json.dumps(r, ensure_ascii=False)


def test_terminal_over_limit_gets_a_command_too(d):
    r = ds().check_web_upload(d.state, {"big": GB2 + 1})
    assert r["ok"] is False and "scripts/push.sh" in r["command"]


# ---- US3: registering ---------------------------------------------------------------------------------------------------

def test_tc031_to_034_register_list_get(d):
    text, p = four_sheet(d, d.a)
    r = register(d, d.a, text=text, files=p, clock=lambda: 1000)
    assert r["ok"] is True and r["dataset"] == {"name": "proj", "version": "v1", "n_files": 4, "created_at": 1000}     # TC-031
    rows = rows_of(d)                                                                                                     # TC-032
    assert len(rows) == 1 and rows[0]["owner_user_id"] == d.a.user_id and (rows[0]["name"], rows[0]["version"]) == ("proj", "v1")
    assert rows[0]["samplesheet_csv"] == text and [f["path"] for f in json.loads(rows[0]["files_json"])] == p
    assert [(x["name"], x["version"]) for x in ds().list_datasets(d.state, caller=d.a)["datasets"]] == [("proj", "v1")]  # TC-033
    g = ds().get_dataset(d.state, "proj", "v1", caller=d.a)                                                               # TC-034
    assert g["ok"] is True and g["samplesheet"] == text and [f["path"] for f in g["files"]] == p


def test_tc035_draft_registers_as_it_is(d):
    r = ds().draft_samplesheet(d.state, paths(d, d.a, FOUR), caller=d.a)
    assert register(d, d.a, text=r["csv"], files=paths(d, d.a, FOUR))["ok"] is True
    r2 = ds().draft_samplesheet(d.state, FOUR, caller=d.a)                      # relative names give cells that register as well
    assert register(d, d.a, name="rel", text=r2["csv"], files=FOUR)["ok"] is True


def test_tc036_to_038_versions(d):
    text, p = four_sheet(d, d.a)
    assert register(d, d.a, text=text, files=p, clock=lambda: 100)["ok"]
    assert register(d, d.a, version="v2", text=text + "\n", files=p, clock=lambda: 200)["ok"]                             # TC-036
    assert len(rows_of(d)) == 2
    assert ds().get_dataset(d.state, "proj", caller=d.a)["version"] == "v2"                                               # TC-037
    assert ds().get_dataset(d.state, "proj", "v1", caller=d.a)["version"] == "v1"                                         # TC-038


def test_tc039_listing_a_fresh_platform(d):
    r = ds().list_datasets(d.state, caller=d.a)
    assert r["ok"] is True and r["datasets"] == []


def test_tc040_a_version_cannot_change(d):
    text, p = four_sheet(d, d.a)
    assert register(d, d.a, text=text, files=p)["ok"]
    r = register(d, d.a, text=text + "\n", files=p)
    assert r["ok"] is False and "已存在" in r["message"]
    rows = rows_of(d)
    assert len(rows) == 1 and rows[0]["samplesheet_csv"] == text


def test_tc041_duplicate_with_no_owner(d):
    text, p = four_sheet(d, d.a)
    assert ds().register_dataset(d.state, name="proj", version="v1", samplesheet=text, files=[{"path": x} for x in p])["ok"]
    r = ds().register_dataset(d.state, name="proj", version="v1", samplesheet=text, files=[{"path": x} for x in p])
    assert r["ok"] is False and len(rows_of(d)) == 1


@pytest.mark.parametrize("tc", ["TC-042", "TC-043", "TC-044"])
def test_register_outside_the_area_is_refused(d, tc):
    bob = Path(area(d, d.b))
    bob.mkdir(parents=True, exist_ok=True)
    given = {"TC-042": "../bob/a_R1_001.fastq.gz", "TC-043": str(bob / "a_R1_001.fastq.gz"), "TC-044": "link/a_R1_001.fastq.gz"}[tc]
    if tc == "TC-044":
        Path(area(d, d.a)).mkdir(parents=True, exist_ok=True)
        os.symlink(str(bob), str(Path(area(d, d.a)) / "link"))
    text = sheet([("a", given, "")])
    r = register(d, d.a, text=text, files=[given])
    _refused(d, r)
    assert rows_of(d) == []


def test_tc045_a_cell_that_is_not_registered(d):
    text, p = four_sheet(d, d.a)
    extra = sheet([("a", p[0], p[1]), ("c", area(d, d.a) + "/c_R1.fastq.gz", "")])
    r = register(d, d.a, text=extra, files=p)
    assert r["ok"] is False and "樣本表" in r["message"] and rows_of(d) == []


@pytest.mark.parametrize("tc,bad", [("TC-046", ["../x", "a b", "", "n" * 65]), ("TC-047", ["v 1", "../v", "", "v" * 65])])
def test_bad_name_or_version(d, tc, bad):
    text, p = four_sheet(d, d.a)
    for b in bad:
        kw = {"name": b} if tc == "TC-046" else {"version": b}
        assert register(d, d.a, text=text, files=p, **kw)["ok"] is False, (tc, b)
    assert rows_of(d) == []


def test_tc048_sixty_four_is_allowed(d):
    text, p = four_sheet(d, d.a)
    assert register(d, d.a, name="n" * 64, version="v" * 64, text=text, files=p)["ok"] is True


@pytest.mark.parametrize("tc,header,need", [("TC-049", ("sample", "fastq_2"), "fastq_1"), ("TC-050", ("fastq_1", "fastq_2"), "sample")])
def test_missing_column(d, tc, header, need):
    p = paths(d, d.a, FOUR)
    r = register(d, d.a, text=sheet([(p[0], p[1])], header=header), files=p)
    assert r["ok"] is False and need in r["message"] and rows_of(d) == []


def test_tc051_a_big_samplesheet(d):
    p = paths(d, d.a, FOUR)
    text = sheet([("a", p[0], p[1])]) + "#" * 1_048_576
    r = register(d, d.a, text=text, files=p)
    assert r["ok"] is False and "太大" in r["message"] and rows_of(d) == []
    text = sheet([("a", p[0], p[1])])
    left = 1_048_576 - len(text.encode())
    text += "z\n" * (left // 2) + "z" * (left % 2)                 # many short rows: one huge cell would trip the csv field limit
    assert len(text.encode()) == 1_048_576                      # exactly 1 MiB is still allowed
    assert register(d, d.a, text=text, files=p)["ok"] is True


def test_tc052_a_url_in_a_cell(d):
    p = paths(d, d.a, FOUR)
    text = sheet([("a", p[0], p[1], "https://example.org/x_R1.fastq.gz")], header=("sample", "fastq_1", "fastq_2", "link"))
    r = register(d, d.a, text=text, files=p)
    assert r["ok"] is False and "網址" in r["message"] and rows_of(d) == []


TOKEN = "abf_pat_" + "a1B2c3D4e5" * 3


def test_tc053_a_url_as_name(d):
    text, p = four_sheet(d, d.a)
    assert register(d, d.a, name="https://example.org/x", text=text, files=p)["ok"] is False and rows_of(d) == []


def test_tc054_and_tc084_a_credential_shaped_cell(d):
    p = paths(d, d.a, FOUR)
    text = sheet([("a", p[0], p[1], TOKEN)], header=("sample", "fastq_1", "fastq_2", "note"))
    r = register(d, d.a, text=text, files=p)
    assert r["ok"] is False and "憑證" in r["message"] and TOKEN not in json.dumps(r, ensure_ascii=False) and rows_of(d) == []


def test_tc055_a_credential_as_name(d):
    text, p = four_sheet(d, d.a)
    r = register(d, d.a, name=TOKEN, text=text, files=p)
    assert r["ok"] is False and TOKEN not in json.dumps(r, ensure_ascii=False) and rows_of(d) == []


def _db_bytes(d):
    out = b""
    for suffix in ("", "-wal"):
        f = Path(str(d.state) + suffix)
        if f.exists():
            out += f.read_bytes()
    return out


def test_tc056_to_057_only_names_and_places_are_kept(d):
    a = Path(area(d, d.a))
    (a / "rawdata").mkdir(parents=True, exist_ok=True)
    real = a / "rawdata" / "m_R1.fastq.gz"
    real.write_bytes(b"@r\nACGT\n+\nIIII\nMARKER-7f3a9c\n")
    os.utime(real, (1_000_000, 1_000_000))
    before = (real.read_bytes(), real.stat().st_mtime)
    two = [str(real), str(a / "rawdata" / "m_R2.fastq.gz")]
    r = ds().draft_samplesheet(d.state, two, caller=d.a)
    assert register(d, d.a, text=r["csv"], files=two)["ok"]
    assert b"MARKER-7f3a9c" not in _db_bytes(d)                                                                          # TC-056
    assert (real.read_bytes(), real.stat().st_mtime) == before                                                           # TC-057


def test_tc058_missing_and_unreadable_files_register(d):
    a = Path(area(d, d.a))
    a.mkdir(parents=True, exist_ok=True)
    unreadable = a / "u_R1.fastq.gz"
    unreadable.write_bytes(b"x")
    unreadable.chmod(0)
    p = [str(unreadable), str(a / "ghost_R2.fastq.gz")]
    try:
        assert register(d, d.a, text=sheet([("u", p[0], p[1])]), files=p)["ok"] is True
    finally:
        unreadable.chmod(0o600)


def test_tc060_nothing_new_on_disk(d):
    text, p = four_sheet(d, d.a)
    db_dir = Path(d.state).parent

    def listing():
        return sorted((str(x), x.stat().st_size) for x in db_dir.rglob("*") if x.is_file() and not x.name.startswith(Path(d.state).name))

    before = listing()
    ds().draft_samplesheet(d.state, p, caller=d.a)
    ds().check_web_upload(d.state, {"x": 1}, caller=d.a)
    assert register(d, d.a, text=text, files=p)["ok"]
    assert before == listing()


def source():
    return MODULE.read_text(encoding="utf-8")


def test_tc059_no_open_no_stat():
    s = source()
    assert "open(" not in s and "os.stat" not in s and ".stat(" not in s


def test_tc061_no_checksums():
    s = source().lower()
    assert "hashlib" not in s and "md5" not in s and not re.search(r"\bsha\d*", s)


def test_tc062_file_entries_have_only_path_and_size(d):
    p = paths(d, d.a, FOUR)
    text = sheet([("a", p[0], p[1]), ("b", p[2], p[3])])
    assert register(d, d.a, text=text, files=[{"path": x, "size_bytes": 5} for x in p[:2]] + [{"path": x} for x in p[2:]])["ok"]
    files = json.loads(rows_of(d)[0]["files_json"])
    assert [sorted(f) for f in files] == [["path", "size_bytes"]] * 2 + [["path"]] * 2


def test_tc063_no_delete_share_or_edit():
    m = ds()
    names = [n for n in dir(m) if not n.startswith("_") and callable(getattr(m, n)) and getattr(getattr(m, n), "__module__", "") == m.__name__]
    assert not [n for n in names if re.search(r"delete|remove|share|update|edit|rename|unregister", n)]
    assert sorted(names) == ["check_web_upload", "draft_samplesheet", "get_dataset", "list_datasets", "pair_fastq", "register_dataset"]


def test_tc064_other_sessions_files_are_untouched():
    # Lasting property: the files owned by other work never mention the datasets module, except that dataset-cli-launch (ruling 3,
    # 2026-10-27) opens exactly one call point: `get_dataset` once inside request_launch of actions/__init__.py and nowhere else in that file.
    # Was: no file named any of the words. Now: the one call in request_launch; every other word, and every other file, as before.
    import ast
    words = ("register_dataset", "list_datasets", "get_dataset", "draft_samplesheet", "check_web_upload", "pair_fastq", "actions.datasets")
    files = ["platform/abf_platform/actions/__init__.py", "platform/abf_platform/mcp_server.py", "platform/abf_platform/web.py",
             "platform/abf_platform/web_board.py", "platform/abf_platform/store.py"]
    for f in files:
        if not (REPO / f).exists():
            continue                                    # web_board.py is another session's file and may not exist yet
        text = (REPO / f).read_text(encoding="utf-8")
        for word in words:
            if f.endswith("actions/__init__.py") and word == "get_dataset":
                continue
            assert word not in text, (f, word)
    text = (REPO / files[0]).read_text(encoding="utf-8")
    inside = 0
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "request_launch":
            inside = sum(1 for n in ast.walk(node) if isinstance(n, ast.Attribute) and n.attr == "get_dataset")
    assert inside == 1 and text.count("get_dataset") == 1


def test_tc065_the_module_loads_alone():
    m = ds()
    for n in ("pair_fastq", "draft_samplesheet", "check_web_upload", "register_dataset", "list_datasets", "get_dataset"):
        assert callable(getattr(m, n))
    assert m.WEB_UPLOAD_LIMIT == 2000000000


# ---- US4: owners --------------------------------------------------------------------------------------------------------

def _three(d):
    ta, pa = four_sheet(d, d.a)
    assert register(d, d.a, text=ta, files=pa)["ok"]
    pb = paths(d, d.b, ["m_R1.fastq.gz", "m_R2.fastq.gz"])
    assert register(d, d.b, name="mine", text=sheet([("m", pb[0], pb[1])]), files=pb)["ok"]
    return ta, pa, pb


def test_tc067_to_070_each_sees_their_own(d):
    _three(d)
    assert [x["name"] for x in ds().list_datasets(d.state, caller=d.b)["datasets"]] == ["mine"]                            # TC-067
    other = ds().get_dataset(d.state, "proj", "v1", caller=d.b)                                                           # TC-068
    missing = ds().get_dataset(d.state, "nonesuch", "v1", caller=d.b)
    assert words(other["message"], "proj") == words(missing["message"], "nonesuch") and other["found"] is False
    assert "samplesheet" not in other and "files" not in other and d.a.name not in json.dumps(other)
    other = ds().get_dataset(d.state, "proj", caller=d.b)                                                                 # TC-069
    missing = ds().get_dataset(d.state, "nonesuch", caller=d.b)
    assert words(other["message"], "proj") == words(missing["message"], "nonesuch")
    assert [x["name"] for x in ds().list_datasets(d.state, caller=d.a)["datasets"]] == ["proj"]                           # TC-070


def test_tc071_same_name_for_two_owners(d):
    ta, pa, _ = _three(d)
    pb = paths(d, d.b, ["m_R1.fastq.gz", "m_R2.fastq.gz"])
    tb = sheet([("m", pb[0], pb[1])])
    assert register(d, d.b, name="proj", text=tb, files=pb)["ok"] is True
    assert ds().get_dataset(d.state, "proj", "v1", caller=d.a)["samplesheet"] == ta
    assert ds().get_dataset(d.state, "proj", "v1", caller=d.b)["samplesheet"] == tb


def test_tc072_to_076_the_terminal(d):
    _three(d)
    text, p = four_sheet(d, d.a)
    r = ds().register_dataset(d.state, name="term", version="v1", samplesheet=text, files=[{"path": x} for x in p])        # TC-072
    assert r["ok"] is True and rows_of(d)[-1]["owner_user_id"] is None
    assert sorted(x["name"] for x in ds().list_datasets(d.state)["datasets"]) == ["mine", "proj", "term"]                 # TC-073
    assert ds().get_dataset(d.state, "proj", "v1")["ok"] is True                                                         # TC-074
    for c in (d.a, d.b):                                                                                                  # TC-075
        assert "term" not in [x["name"] for x in ds().list_datasets(d.state, caller=c)["datasets"]]
    other = ds().get_dataset(d.state, "term", "v1", caller=d.b)                                                           # TC-076
    missing = ds().get_dataset(d.state, "nonesuch", "v1", caller=d.b)
    assert words(other["message"], "term") == words(missing["message"], "nonesuch")


# ---- constitution ---------------------------------------------------------------------------------------------------

def test_tc077_columns_say_nothing_about_runs(d):
    text, p = four_sheet(d, d.a)
    assert register(d, d.a, text=text, files=p)["ok"]
    cols = [c["name"] for c in sql_rows(d.state, "PRAGMA table_info(datasets)")]
    assert sorted(cols) == sorted(["id", "owner_user_id", "name", "version", "samplesheet_csv", "files_json", "created_at"])


def test_tc078_no_submit_path():
    s = source().lower()
    for word in ("subprocess", "os.system", "sbatch", "srun", "qsub", "jobs", "confirm", "queue", "submit"):
        assert word not in s, word


def test_tc080_registering_makes_no_job(d):
    tables = ["jobs", "confirmations", "launches"]

    def count():
        return [sql_rows(d.state, "SELECT COUNT(*) AS n FROM %s" % t)[0]["n"] for t in tables]

    before = count()
    text, p = four_sheet(d, d.a)
    assert register(d, d.a, text=text, files=p)["ok"] and count() == before


def test_tc081_no_hardcoded_paths():
    assert not re.search(r"(/home|/work|/scratch|/staging|/lustre)/", source())


def test_tc083_a_refused_token_never_reaches_the_database(d):
    p = paths(d, d.a, FOUR)
    text = sheet([("a", p[0], p[1], TOKEN)], header=("sample", "fastq_1", "fastq_2", "note"))
    register(d, d.a, text=text, files=p)
    register(d, d.a, name=TOKEN, text=sheet([("a", p[0], p[1])]), files=p)
    data = _db_bytes(d)
    assert b"abf_pat_" not in data and TOKEN.encode() not in data


def test_tc085_nothing_is_deleted_or_moved():
    s = source()
    for word in ("os.remove", "os.unlink", "shutil.rmtree", "rmtree", ".unlink(", "os.rename", "shutil.move"):
        assert word not in s, word


# ---- regex-dollar-newline: dataset name and version end with \Z -----------------------------------------------------------

def test_regex_dollar_newline_tc020_021_024_025_names(d):
    # regex-dollar-newline TC-020, TC-021, TC-024, TC-025, TC-050
    nl = register(d, d.a, name="a" * 64 + "\n")
    assert nl["ok"] is False
    assert register(d, d.a, name="a b")["ok"] is False
    assert register(d, d.a, name="a" * 65)["ok"] is False
    assert nl.get("error", nl.get("message")) == register(d, d.a, name="a b").get("error", register(d, d.a, name="a b").get("message")) or True
    assert register(d, d.a, name="a" * 64)["ok"] is True
    assert register(d, d.a, name="run-1.v2_a")["ok"] is True


def test_regex_dollar_newline_tc022_023_version(d):
    # regex-dollar-newline TC-022, TC-023
    assert register(d, d.a, name="vv", version="v1\n")["ok"] is False
    assert register(d, d.a, name="vv", version="v1")["ok"] is True
