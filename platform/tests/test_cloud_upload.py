# Nothing existing: tests of the cloud-upload task (gs:// locations, whose prefix a location lies in, the 2 GB command, the streaming core); the prefix rule and the sink protocol are ours, and no library plays a fake bucket.
"""cloud-upload (platform half): a Dataset may be registered at gs:// locations of a Google Batch environment's bucket.
Test case ids (TC-001 ...) refer to specs/cloud-upload/test-case.md. Nothing here reaches the network, starts a program or reads a
key file; the sink and the chunks are fakes."""
import csv
import inspect
import io
import json
import os
import re
import sqlite3
import tracemalloc
from pathlib import Path

import pytest

from human_harness import World
from owner_harness import Duo, sql_rows

HERE = Path(__file__).resolve().parent
PLATFORM = HERE.parent
PKG = PLATFORM / "abf_platform"
STORE_SRC = PKG / "cloud_store.py"
DATASETS_SRC = PKG / "actions" / "datasets.py"
GCB = "googlebatch-platform"
GB2 = 2_000_000_000
A = "gs://lab-bucket/uploads/alice/"
B = "gs://lab-bucket/uploads/bob/"
TOKEN = "abf_" + "pat_" + "a1B2c3D4e5" * 3
FOUR = ["a_R1.fastq.gz", "a_R2.fastq.gz", "b_R1.fastq.gz", "b_R2.fastq.gz"]


def cs():
    from abf_platform import cloud_store
    return cloud_store


def ds():
    from abf_platform.actions import datasets
    return datasets


@pytest.fixture
def d(tmp_path, monkeypatch):
    duo = Duo(World(tmp_path, monkeypatch))
    duo.tmp = tmp_path
    return duo


def make_env(d, name, bucket, owner, status=None, platform=GCB, config=None):
    from abf_platform import compute_envs
    cfg = {"project": "lab-project-1", "location": "europe-west2", "workDir": "gs://%s/work" % bucket} if config is None else config
    compute_envs.create(d.state, {"name": name, "platform": platform, "agent": "a1", "owner_user_id": owner.user_id, "config": cfg})
    if status:
        con = sqlite3.connect(str(d.state))
        with con:
            con.execute("UPDATE compute_envs SET status = ? WHERE name = ?", (status, name))
        con.close()


@pytest.fixture
def cloud(d):
    make_env(d, "gcb1", "lab-bucket", d.a)
    make_env(d, "gcb2", "other-bucket", d.b)
    return d


def ce_of(bucket="lab-bucket", platform=GCB):
    return {"platform": platform, "config": {"workDir": "gs://%s/work" % bucket}}


def sheet(rows, header=("sample", "fastq_1", "fastq_2")):
    out = io.StringIO()
    wr = csv.writer(out, lineterminator="\n")
    wr.writerow(header)
    for r in rows:
        wr.writerow(r)
    return out.getvalue()


def four(prefix=A):
    p = [prefix + n for n in FOUR]
    return sheet([("a", p[0], p[1]), ("b", p[2], p[3])]), p


def register(d, caller, destination="gcb1", name="proj", version="v1", text=None, files=None, **kw):
    if text is None:
        text, files = four()
    return ds().register_dataset(d.state, name=name, version=version, samplesheet=text,
                                 files=[f if isinstance(f, dict) else {"path": f} for f in files], caller=caller,
                                 destination=destination, **kw)


def rows_of(d):
    try:
        return sql_rows(d.state, "SELECT * FROM datasets ORDER BY id")
    except sqlite3.OperationalError:
        return []


def words(text, name):
    return re.sub(re.escape(name), "<name>", str(text))


def listing(root):
    out = []
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and ".db" not in p.name:
            out.append((str(p), p.stat().st_size))
    return out


def db_bytes(d):
    out = b""
    for suffix in ("", "-wal"):
        f = Path(str(d.state) + suffix)
        if f.exists():
            out += f.read_bytes()
    return out


# ---- US1: register at a cloud place --------------------------------------------------------------------------------------

def test_register_a_cloud_dataset(cloud):
    # TC-001, TC-002
    r = register(cloud, cloud.a)
    assert r["ok"] is True, r
    rows = rows_of(cloud)
    assert len(rows) == 1 and rows[0]["owner_user_id"] == cloud.a.user_id
    got = ds().get_dataset(cloud.state, "proj", "v1", caller=cloud.a)
    assert [f["path"] for f in got["files"]] == [A + n for n in FOUR]
    assert all(set(f) <= {"path", "size_bytes"} for f in got["files"]) and all(f["path"].startswith("gs://") for f in got["files"])
    sized = register(cloud, cloud.a, version="v2", files=[{"path": A + n, "size_bytes": 5} for n in FOUR], text=four()[0])
    assert sized["ok"]
    assert [sorted(f) for f in json.loads(rows_of(cloud)[1]["files_json"])] == [["path", "size_bytes"]] * 4


def test_the_datasets_table_has_no_new_column(cloud):
    # TC-003
    assert register(cloud, cloud.a)["ok"]
    cols = [c["name"] for c in sql_rows(cloud.state, "PRAGMA table_info(datasets)")]
    assert sorted(cols) == sorted(["id", "owner_user_id", "name", "version", "samplesheet_csv", "files_json", "created_at"])


def test_registering_does_not_need_an_available_environment(d):
    # TC-004
    make_env(d, "gcb1", "lab-bucket", d.a, status="creating")
    assert register(d, d.a)["ok"] is True


def test_the_terminal_registers_below_uploads(cloud):
    # TC-005
    text, p = four("gs://lab-bucket/uploads/")
    assert register(cloud, None, text=text, files=p)["ok"] is True
    assert rows_of(cloud)[0]["owner_user_id"] is None


def test_a_cloud_draft_pairs_full_locations(cloud):
    # TC-006
    r = ds().draft_samplesheet(cloud.state, [A + n for n in FOUR], caller=cloud.a, destination="gcb1")
    assert r["ok"] and len(r["pairs"]) == 2 and r["unpaired"] == []
    assert "gs://" in r["csv"] and {p["sample"] for p in r["pairs"]} == {"a", "b"}


def test_a_cloud_draft_takes_single_level_names(cloud):
    # TC-007
    r = ds().draft_samplesheet(cloud.state, ["a_R1.fastq.gz", "a_R2.fastq.gz"], caller=cloud.a, destination="gcb1")
    assert r["ok"] and len(r["pairs"]) == 1
    assert (r["pairs"][0]["fastq_1"], r["pairs"][0]["fastq_2"]) == (A + "a_R1.fastq.gz", A + "a_R2.fastq.gz")


def test_a_draft_writes_nothing(cloud):
    # TC-008
    before = (listing(cloud.tmp), listing(cloud.uploads))
    ds().draft_samplesheet(cloud.state, [A + n for n in FOUR], caller=cloud.a, destination="gcb1")
    ds().draft_samplesheet(cloud.state, [B + FOUR[0]], caller=cloud.a, destination="gcb1")
    assert (listing(cloud.tmp), listing(cloud.uploads)) == before


def test_register_and_check_leave_no_new_file(cloud):
    # TC-009
    before = (listing(cloud.tmp), listing(cloud.uploads))
    assert register(cloud, cloud.a)["ok"]
    ds().check_web_upload(cloud.state, {"big.fastq.gz": GB2 + 5}, caller=cloud.a, destination="gcb1")
    assert (listing(cloud.tmp), listing(cloud.uploads)) == before


def test_destination_is_a_keyword_defaulting_to_none():
    # TC-010, TC-022
    expected = {"draft_samplesheet": ["platform_path", "files"], "check_web_upload": ["platform_path", "sizes"],
                "register_dataset": ["platform_path"]}
    for fn, positional in expected.items():
        sig = inspect.signature(getattr(ds(), fn))
        p = sig.parameters["destination"]
        assert p.default is None and p.kind is inspect.Parameter.KEYWORD_ONLY
        assert [n for n, x in sig.parameters.items() if x.kind is not inspect.Parameter.KEYWORD_ONLY] == positional


def test_a_negative_size_is_refused(cloud):
    # TC-012
    text, p = four()
    r = register(cloud, cloud.a, text=text, files=[{"path": p[0], "size_bytes": -1}] + p[1:])
    assert r["ok"] is False and "0 以上的整數" in r["message"] and rows_of(cloud) == []


# ---- US2: what is not yours is refused -----------------------------------------------------------------------------------

def refused(r, d_):
    assert r["ok"] is False and rows_of(d_) == []
    return r["message"]


def test_a_cloud_dataset_cannot_name_somebody_elses_prefix(cloud):
    # TC-013
    text, p = four(B)
    msg = refused(register(cloud, cloud.a, text=text, files=p), cloud)
    assert A in msg and "bob" not in msg


def test_a_cloud_dataset_cannot_leave_the_environments_bucket(cloud):
    # TC-014
    text, p = four("gs://other-bucket/uploads/alice/")
    msg = refused(register(cloud, cloud.a, text=text, files=p), cloud)
    assert "workDir" in msg and "bucket" in msg


def test_a_prefix_that_only_starts_alike_is_somebody_else(cloud):
    # TC-015
    text, p = four("gs://lab-bucket/uploads/alicex/")
    refused(register(cloud, cloud.a, text=text, files=p), cloud)


def test_a_prefix_alone_is_not_a_file(cloud):
    # TC-016
    refused(register(cloud, cloud.a, text=sheet([("a", A, "")]), files=[A]), cloud)


def test_dots_are_refused(cloud):
    # TC-017
    bad = A + "../bob/a_R1.fastq.gz"
    refused(register(cloud, cloud.a, text=sheet([("a", bad, "")]), files=[bad]), cloud)


def test_local_and_cloud_paths_cannot_be_mixed(cloud):
    # TC-018
    local = "/data/x_R2" + ".fq"
    msg = refused(register(cloud, cloud.a, text=sheet([("a", A + "a_R1.fastq.gz", local)]), files=[A + "a_R1.fastq.gz", local]), cloud)
    assert "不能同時混本機路徑與雲端位置" in msg


def test_a_cell_that_is_not_a_registered_file_is_refused(cloud):
    # TC-019
    text, p = four()
    text = sheet([("a", p[0], p[1]), ("c", A + "c_R1.fastq.gz", "")])
    msg = refused(register(cloud, cloud.a, text=text, files=p), cloud)
    assert "不在登記的檔案內" in msg


def test_a_url_cell_is_still_refused(cloud):
    # TC-020
    text, p = four()
    text = sheet([("a", p[0], p[1], "https://example.org/x_R1.fastq.gz")], header=("sample", "fastq_1", "fastq_2", "extra"))
    assert "網址" in refused(register(cloud, cloud.a, text=text, files=p), cloud)


def test_a_credential_shaped_value_is_refused_and_never_stored(cloud):
    # TC-021, TC-022
    bad = A + TOKEN
    r = register(cloud, cloud.a, text=sheet([("a", bad, "")]), files=[bad])
    assert r["ok"] is False and rows_of(cloud) == []
    assert b"abf_pat_" not in db_bytes(cloud)
    assert TOKEN not in json.dumps(r) and "abf_pat_" not in json.dumps(r)


def test_one_foreign_place_refuses_the_whole_draft(cloud):
    # TC-023
    r = ds().draft_samplesheet(cloud.state, [A + FOUR[0], A + FOUR[1], A + FOUR[2], B + FOUR[3]], caller=cloud.a, destination="gcb1")
    assert r["ok"] is False and "pairs" not in r and "csv" not in r


def test_someone_elses_environment_answers_like_a_missing_one(cloud):
    # TC-024, TC-025, TC-026
    text, p = four()
    one, two = (register(cloud, cloud.b, destination=n, text=text, files=p) for n in ("gcb1", "no-such-env"))
    assert one["ok"] is False and words(one, "gcb1") == words(two, "no-such-env") and rows_of(cloud) == []
    one, two = (ds().draft_samplesheet(cloud.state, p, caller=cloud.b, destination=n) for n in ("gcb1", "no-such-env"))
    assert one["ok"] is False and words(one, "gcb1") == words(two, "no-such-env")
    one, two = (ds().check_web_upload(cloud.state, {"x": 1}, caller=cloud.b, destination=n) for n in ("gcb1", "no-such-env"))
    assert one["ok"] is False and words(one, "gcb1") == words(two, "no-such-env")


def test_a_missing_environment_is_said_plainly(cloud):
    # TC-027
    r = register(cloud, cloud.a, destination="no-such-env")
    assert r["ok"] is False and "找不到計算環境" in r["message"] and rows_of(cloud) == []


def test_an_environment_that_cannot_hold_cloud_data_is_refused(d):
    # TC-028
    d.bobs_environment("slurm1", owner=d.a.user_id)
    make_env(d, "plain1", "x", d.a, platform="awscloud-platform", config={})
    for name in ("slurm1", "plain1"):
        r = register(d, d.a, destination=name)
        assert r["ok"] is False and "不能放雲端資料" in r["message"]
    assert rows_of(d) == []


def test_another_person_does_not_see_the_dataset(cloud):
    # TC-029, TC-030
    assert register(cloud, cloud.a)["ok"]
    assert ds().list_datasets(cloud.state, caller=cloud.b)["datasets"] == []
    seen = ds().get_dataset(cloud.state, "proj", "v1", caller=cloud.b)
    nothing = ds().get_dataset(cloud.state, "zzz", "v1", caller=cloud.b)
    assert seen["ok"] is False and words(seen, "proj") == words(nothing, "zzz")


def test_refusals_are_plain_sentences(cloud):
    # TC-031
    text, p = four(B)
    replies = [register(cloud, cloud.a, text=text, files=p),
               register(cloud, cloud.a, text=text.replace(B, "gs://other-bucket/"), files=[x.replace(B, "gs://other-bucket/") for x in p]),
               register(cloud, cloud.a, text=sheet([("a", A + "../x", "")]), files=[A + "../x"]),
               register(cloud, cloud.a, text=sheet([("a", A + FOUR[0], "/data/x")]), files=[A + FOUR[0], "/data/x"]),
               register(cloud, cloud.a, destination="nope"),
               ds().check_web_upload(cloud.state, {"x": 1}, caller=cloud.a, destination="nope")]
    d_ = cloud
    d_.bobs_environment("slurm1", owner=d_.a.user_id)
    replies.append(register(d_, d_.a, destination="slurm1"))
    for r in replies:
        assert r["ok"] is False and r["message"]
        assert not re.search(r"Traceback|SELECT |INSERT |\.py\b|%s" % re.escape(str(cloud.tmp)), r["message"])


# ---- US3: over 2 GB --------------------------------------------------------------------------------------------------------

def check(d_, sizes, caller=None, dest="gcb1"):
    return ds().check_web_upload(d_.state, sizes, caller=d_.a if caller is None else caller, destination=dest)


def test_exactly_two_gb_is_taken(cloud):
    # TC-032
    r = check(cloud, {"x_R1.fastq.gz": GB2})
    assert r["ok"] is True and r["accepted"] == ["x_R1.fastq.gz"] and r["over"] == []


def test_one_byte_more_gets_a_command(cloud):
    # TC-033, TC-034, TC-035, TC-036
    r = check(cloud, {"big_R1.fastq.gz": GB2 + 1})
    assert r["ok"] is False and r["over"] == ["big_R1.fastq.gz"]
    assert r["command"].startswith("gcloud storage cp ") and A in r["command"] and "bob" not in r["command"]
    assert "如果檔案已經在這個 bucket 裡，就把它們放進同一個前綴：%s" % A in r["message"]
    assert "push.sh" not in r["message"] and "國網" not in r["message"]
    assert {"ok", "message", "over", "command", "accepted"} <= set(r)


def test_only_the_big_one_is_listed(cloud):
    # TC-037
    r = check(cloud, {"a": 500_000_000, "b": 500_000_000, "c": 500_000_000, "big": 2_500_000_000})
    assert r["over"] == ["big"] and r["accepted"] == ["a", "b", "c"]


def test_the_limit_is_per_file(cloud):
    # TC-038
    r = check(cloud, {n: 1_999_999_999 for n in "wxyz"})
    assert r["ok"] is True and len(r["accepted"]) == 4


def test_bad_sizes_are_refused_like_before(cloud):
    # TC-039
    for sizes in ({"x": -1}, {"x": "12"}, {"x": 1.5}):
        cloud_reply = check(cloud, sizes)
        plain = ds().check_web_upload(cloud.state, sizes, caller=cloud.a)
        assert cloud_reply["ok"] is False and cloud_reply == plain


def test_the_terminal_gets_the_prefix_without_a_name(cloud):
    # TC-040
    r = ds().check_web_upload(cloud.state, {"big": GB2 + 1}, caller=None, destination="gcb1")
    assert "gs://lab-bucket/uploads/rawdata/" in r["command"] and "gs://lab-bucket/uploads/" in r["message"]


def test_the_big_file_command_is_one_line_with_only_the_bucket_prefix():
    # TC-041
    line = cs().big_file_command(ce_of(), "alice")
    assert "\n" not in line and line.startswith("gcloud storage cp ")
    assert "gs://lab-bucket/uploads/alice/rawdata/" in line and "<你電腦上的資料夾>" in line
    assert not re.search(r"lab-project|gcp-sa|\.json", line)


# ---- US4: the language of locations --------------------------------------------------------------------------------------

BENT = ["s3://b/x", "https://b/x", "gs://B/x", "gs://ab/x", "gs://b-ok/../x", "gs://b-ok/a/../../x", "gs://b-ok/", "gs://b-ok//x",
        "gs://b-ok/a" + chr(0) + "b", "gs://b-ok/a\nb", "gs://b-ok/" + "x" * 1025]


def test_parse_gs_accepts_a_plain_location():
    # TC-042
    assert cs().parse_gs("gs://lab-bucket/uploads/alice/a_R1.fastq.gz") == ("lab-bucket", "uploads/alice/a_R1.fastq.gz")


@pytest.mark.parametrize("url", BENT)
def test_parse_gs_refuses_the_bent_ones(url):
    # TC-043, TC-044
    with pytest.raises(cs().CloudPathError) as e:
        cs().parse_gs(url)
    assert str(e.value) and not re.search(r"Traceback|File \"|CloudPathError|parse_gs|_BUCKET", str(e.value))


@pytest.mark.parametrize("url", ["s3://b/x", "https://b/x", "file://b/x"])
def test_only_gs_is_taken(url):
    # TC-045
    with pytest.raises(cs().CloudPathError) as e:
        cs().parse_gs(url)
    assert "只收 gs://" in str(e.value)


@pytest.mark.parametrize("bucket", ["abc", "a" * 63, "a-b_c.d", "1ab2"])
def test_bucket_names_that_are_fine(bucket):
    # TC-046
    assert cs().parse_gs("gs://%s/x" % bucket) == (bucket, "x")


@pytest.mark.parametrize("bucket", ["ab", "a" * 64, "Abc", "-abc", "abc."])
def test_bucket_names_that_are_not(bucket):
    # TC-047
    with pytest.raises(cs().CloudPathError):
        cs().parse_gs("gs://%s/x" % bucket)


def test_the_name_is_at_most_1024_bytes_not_characters():
    # TC-048, TC-049, TC-050
    assert cs().parse_gs("gs://b-ok/" + "x" * 1024)[1] == "x" * 1024
    for name in ("x" * 1025, "中" * 600):
        with pytest.raises(cs().CloudPathError):
            cs().parse_gs("gs://b-ok/" + name)


def test_encoded_dots_are_literal():
    # TC-051
    url = A + "%2e%2e/bob/x"
    assert cs().parse_gs(url)[1] == "uploads/alice/%2e%2e/bob/x"
    assert cs().inside_prefix(url, A) is True


def test_inside_prefix_needs_the_same_bucket_and_something_after():
    # TC-052, TC-053, TC-054, TC-055
    assert cs().inside_prefix(A + "x", A) is True
    assert cs().inside_prefix(A, A) is False
    assert cs().inside_prefix("gs://other-bucket/uploads/alice/x", A) is False
    assert cs().inside_prefix("gs://lab-bucket/uploads/alicex/x", A) is False


def test_workdir_bucket_needs_a_google_batch_environment():
    # TC-056, TC-057, TC-058
    assert cs().workdir_bucket(ce_of()) == "lab-bucket"
    assert cs().workdir_bucket({"platform": GCB, "config": {"workDir": "gs://lab-bucket"}}) == "lab-bucket"
    for bad in (ce_of(platform="slurm-platform"), {"platform": GCB, "config": {}}, {"platform": "awscloud-platform", "config": {}}):
        with pytest.raises(cs().CloudPathError):
            cs().workdir_bucket(bad)


def test_upload_prefix_and_object_url():
    # TC-059, TC-060
    assert cs().upload_prefix(ce_of(), "alice") == A
    assert cs().upload_prefix(ce_of(), None) == "gs://lab-bucket/uploads/"
    assert cs().object_url(ce_of(), "alice", "a_R1.fastq.gz") == A + "a_R1.fastq.gz"


@pytest.mark.parametrize("name", ["x/y", "x\\y", "..", "a" + chr(0) + "b", "", "a" * 256])
def test_object_url_refuses_the_bent_names(name):
    # TC-061
    with pytest.raises(cs().CloudPathError):
        cs().object_url(ce_of(), "alice", name)


def test_object_url_takes_255_characters():
    # TC-062
    assert cs().object_url(ce_of(), "alice", "a" * 255).endswith("a" * 255)


# ---- US5: the streaming core ---------------------------------------------------------------------------------------------

class Sink:
    def __init__(self, fail_write=None):
        self.events, self.fail_write = [], fail_write

    def write(self, data):
        if self.fail_write:
            raise self.fail_write
        self.events.append(("write", bytes(data)))

    def close(self):
        self.events.append(("close",))

    def abort(self):
        self.events.append(("abort",))

    def count(self, kind):
        return len([e for e in self.events if e[0] == kind])


class Source:
    """Chunks that count how many were taken."""
    def __init__(self, sizes, then=None):
        self.sizes, self.taken, self.then = sizes, 0, then

    def __iter__(self):
        for n in self.sizes:
            self.taken += 1
            yield b"x" * n
        if self.then:
            raise self.then


def test_stream_into_hands_every_chunk_to_the_sink_and_closes():
    # TC-063
    sink, chunks = Sink(), [b"a" * 200, b"b" * 200, b"c" * 200, b"d" * 200, b"e" * 200]
    r = cs().stream_into(iter(chunks), sink, declared_size=1000, limit=GB2)
    assert r == {"ok": True, "received": 1000}
    assert [e[1] for e in sink.events if e[0] == "write"] == chunks and sink.count("close") == 1 and sink.count("abort") == 0


def test_stream_into_stops_at_the_first_byte_over_the_declared_size():
    # TC-064, TC-065, TC-066
    sink, src = Sink(), Source([400, 400, 201, 100, 100])
    r = cs().stream_into(src, sink, declared_size=1000, limit=GB2)
    assert r["ok"] is False and r["message"] and "received" in r
    assert sink.count("abort") == 1 and sink.count("close") == 0
    assert src.taken == 3


def test_stream_into_refuses_a_declared_size_over_the_limit_before_reading():
    # TC-067
    sink, src = Sink(), Source([10, 10])
    r = cs().stream_into(src, sink, declared_size=GB2 + 1, limit=GB2)
    assert r["ok"] is False and sink.count("write") == 0 and src.taken == 0


def test_stream_into_short_is_an_error():
    # TC-068
    sink = Sink()
    r = cs().stream_into(Source([500, 499]), sink, declared_size=1000, limit=GB2)
    assert r["ok"] is False and sink.count("abort") >= 1 and sink.count("close") == 0


def test_stream_into_exactly_at_the_limit_is_not_over():
    # TC-069
    r = cs().stream_into(Source([600, 400]), Sink(), declared_size=1000, limit=1000)
    assert r["ok"] is True and r["received"] == 1000


def test_a_failing_chunk_source_or_sink_aborts_and_hides_the_text():
    # TC-070, TC-071, TC-072
    boom = RuntimeError("token=abc123 /ho" + "me/x/gcp-sa.json")
    sink = Sink()
    r1 = cs().stream_into(Source([100], then=boom), sink, declared_size=1000, limit=GB2)
    sink2 = Sink(fail_write=boom)
    r2 = cs().stream_into(Source([100]), sink2, declared_size=100, limit=GB2)
    for r, s in ((r1, sink), (r2, sink2)):
        assert r["ok"] is False and s.count("abort") == 1
        assert not re.search(r"abc123|gcp-sa|/home", json.dumps(r))
    assert "傳輸中斷" in r1["message"]


def test_stream_into_never_holds_more_than_one_chunk():
    # TC-073
    block = b"z" * (1 << 20)

    def chunks():
        for _ in range(200):
            yield block

    class Drop:
        def write(self, data):
            pass

        def close(self):
            pass

        def abort(self):
            pass

    tracemalloc.start()
    try:
        r = cs().stream_into(chunks(), Drop(), declared_size=200 << 20, limit=GB2)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert r["ok"] is True and peak < 8 << 20


def test_the_core_writes_no_file(tmp_path, monkeypatch):
    # TC-074
    monkeypatch.chdir(tmp_path)
    before = (listing(tmp_path), listing(os.getcwd()))
    cs().stream_into(Source([500, 500]), Sink(), declared_size=1000, limit=GB2)
    cs().stream_into(Source([600, 600]), Sink(), declared_size=1000, limit=GB2)
    assert (listing(tmp_path), listing(os.getcwd())) == before


# ---- US6: scope and source scans -----------------------------------------------------------------------------------------

def public(mod):
    return sorted(n for n in dir(mod) if not n.startswith("_") and inspect.isfunction(getattr(mod, n))
                  and getattr(getattr(mod, n), "__module__", "") == mod.__name__)


def test_no_public_function_was_added_to_datasets():
    # TC-077
    names = public(ds())
    assert names == ["check_web_upload", "draft_samplesheet", "get_dataset", "list_datasets", "pair_fastq", "register_dataset"]
    assert not [n for n in names if re.search(r"delete|remove|share|update|edit|rename|unregister", n)]


def test_cloud_store_has_nothing_about_deleting_or_reminding():
    # TC-078
    low = STORE_SRC.read_text(encoding="utf-8").lower()
    assert not [n for n in public(cs()) if re.search(r"delete|remove|expire|remind|unlink", n)]
    for word in ("delete", "remove", "expire", "remind", "unlink", "rmtree"):
        assert word not in low, word


def test_no_checksum_words_and_no_hash_in_the_answer():
    # TC-079
    for src in (STORE_SRC, DATASETS_SRC):
        low = src.read_text(encoding="utf-8").lower()
        assert "hashlib" not in low and "md5" not in low and not re.search(r"\bsha\d*", low)
    r = cs().stream_into(Source([10]), Sink(), declared_size=10, limit=GB2)
    assert set(r) == {"ok", "received"}
    assert set(cs().stream_into(Source([20]), Sink(), declared_size=10, limit=GB2)) == {"ok", "message", "received"}


def test_s3_is_not_taken(cloud):
    # TC-080
    p = ["s3://lab-bucket/uploads/alice/" + n for n in FOUR]
    r = register(cloud, cloud.a, text=sheet([("a", p[0], p[1])]), files=p)
    assert r["ok"] is False and "只收 gs://" in r["message"] and rows_of(cloud) == []


def test_no_cloud_dependency_was_added():
    # TC-081
    for name in ("pyproject.toml", "constraints.txt"):
        assert "google" not in (PLATFORM / name).read_text(encoding="utf-8").lower()


def test_cloud_store_has_no_io_network_or_process_words():
    # TC-088
    s = STORE_SRC.read_text(encoding="utf-8")
    for word in ("open(", "subprocess", "os.system", "socket", "urllib", "httpx", "requests", "import google", "boto3", "azure"):
        assert word not in s, word


def test_the_word_station_appears_nowhere_in_the_new_or_changed_sources():
    # TC-089
    for src in (STORE_SRC, DATASETS_SRC):
        text = src.read_text(encoding="utf-8").lower()
        assert "station" not in text
        assert "station" not in re.sub(r"[\"'+\s]", "", text)


def test_no_hardcoded_place_in_the_sources():
    # TC-090
    for src in (STORE_SRC, DATASETS_SRC):
        s = src.read_text(encoding="utf-8")
        assert "lab-bucket" not in s and not re.search(r"(/home|/work|/scratch|/staging|/lustre)\b", s), src.name


def test_no_key_file_word_in_the_new_sources():
    # TC-091
    for src in (STORE_SRC, DATASETS_SRC):
        s = src.read_text(encoding="utf-8")
        for word in ("gcp-sa", "GOOGLE_APPLICATION_CREDENTIALS", "CLOUDSDK", ".json"):
            assert word not in s, (src.name, word)


def test_no_function_takes_a_key_file_or_a_secret():
    # TC-092
    bad = re.compile(r"key|cred|secret|token|passw|pem", re.I)
    names = []
    for mod in (cs(), ds()):
        for n in public(mod):
            names += list(inspect.signature(getattr(mod, n)).parameters)
    assert not [n for n in names if bad.search(n)]
    assert "destination" in names
