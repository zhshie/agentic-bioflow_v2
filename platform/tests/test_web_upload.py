# Nothing existing: tests of the web upload page (web-upload-page: GET /upload, POST /upload, GET /upload/{batch}); the page, its batch record and its rules are ours, and no library plays a browser that posts a multipart form to this site.
"""web-upload-page. Test case ids (TC-001 ...) refer to specs/web-upload-page/test-case.md. Everything runs in process on databases under tmp_path: no network,
no program is started, no real cloud. The "jobs" are rows of platform.db; a test plays the agent of the platform host by changing a row's result."""
import ast
import asyncio
import json
import os
import re
import sqlite3
import stat
import time
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR
from human_harness import World, csrf_of
from owner_harness import Duo, sql_exec, sql_rows
from test_web_board import cjk, hrefs, no_cjk, pane, plain, style_of

PKG = PLATFORM_DIR / "abf_platform"
GCB = "googlebatch-platform"
AWS = "awsbatch-platform"
R1, R2 = "sampleA_R1.fastq.gz", "sampleA_R2.fastq.gz"
BOUNDARY = "----abfUploadTestBoundary"
CTYPE = "multipart/form-data; boundary=" + BOUNDARY
FETCH = object()
SHEET_OK = "sample,fastq_1,fastq_2\nsampleA,%s,%s\n" % (R1, R2)
AKID = "AK" + "IA" + "IOSFODNN7EXAMPLE"        # built in pieces: no tracked file holds a key-shaped string
SECRET_WORDS = ("put_upload", "enqueue", ".incoming-", ".batches", "Traceback", "sqlite", "SELECT ")
BANNED = "用過 選好 寫死 自己填 自己調整 你還沒 還沒有 還不能 這個 這份 這條 這一版 一下 弄 搞 東西 喔 啦 吧 囉 蠻 超".split()


def multipart(fields=(), files=(), sheet=None, boundary=BOUNDARY, empty_sheet=True):
    """The bytes a browser sends: text fields, then FASTQ parts (name, bytes) and the samplesheet part. A file name may be bytes (raw)."""
    out = []
    for key, value in fields:
        out.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n' % (boundary, key)).encode("utf-8") + value.encode("utf-8") + b"\r\n")
    for filename, data in files:
        fn = filename if isinstance(filename, bytes) else filename.encode("utf-8")
        out.append(('--%s\r\nContent-Disposition: form-data; name="fastq"; filename="' % boundary).encode() + fn +
                   b'"\r\nContent-Type: application/octet-stream\r\n\r\n' + data + b"\r\n")
    if sheet is not None:
        out.append(('--%s\r\nContent-Disposition: form-data; name="samplesheet"; filename="sheet.csv"\r\nContent-Type: text/csv\r\n\r\n' % boundary).encode()
                   + (sheet if isinstance(sheet, bytes) else sheet.encode("utf-8")) + b"\r\n")
    elif empty_sheet:
        out.append(('--%s\r\nContent-Disposition: form-data; name="samplesheet"; filename=""\r\nContent-Type: application/octet-stream\r\n\r\n\r\n' % boundary).encode())
    out.append(("--%s--\r\n" % boundary).encode())
    return b"".join(out)


def upload_token(text):
    m = re.search(r'action="/upload[^"]*"[^>]*><input type="hidden" name="csrf" value="([^"]+)"', text)
    return m.group(1) if m else None


class Up:
    """alice and bob, each with a cloud compute environment (gcb1 and gcb2) whose agent is online; the slurm environment that the setup made is bob's."""

    def __init__(self, tmp_path, monkeypatch):
        self.w = World(tmp_path, monkeypatch)
        self.d = Duo(self.w)
        self.a, self.b = self.d.a, self.d.b
        self.state = self.w.ip.state_db
        self.tokens = self.w.ip.tokens
        self.uploads = self.d.uploads
        sql_exec(self.state, "UPDATE compute_envs SET owner_user_id = ? WHERE name = 'lab-a'", (self.b.user_id,))
        self.env("gcb1", "lab-bucket", self.a)
        self.env("gcb2", "other-bucket", self.b)
        self.clients = {}

    # ---- the world -----------------------------------------------------------------------------------------------------
    def env(self, name, bucket, owner, platform=GCB, status="available"):
        from abf_platform import agents, compute_envs
        agent = "ag-" + name
        agents.register(self.state, agent, "0.1.0", time.time, owner_user_id=owner.user_id)
        if platform == AWS:
            fields = {"name": name, "platform": AWS, "agent": agent, "owner_user_id": owner.user_id, "credentialsId": "aws-cred",
                      "config": {"region": "eu-west-1", "workDir": "s3://%s/work" % bucket, "jobQueue": "lab-queue"}}
        else:
            fields = {"name": name, "platform": platform, "agent": agent, "owner_user_id": owner.user_id,
                      "config": {"project": "lab-project-1", "location": "europe-west2", "workDir": "gs://%s/work" % bucket}}
        compute_envs.create(self.state, fields)
        sql_exec(self.state, "UPDATE compute_envs SET status = ?, checked_ok = 1 WHERE name = ?", (status, name))

    def slurm_for_alice(self):
        sql_exec(self.state, "UPDATE compute_envs SET owner_user_id = ?, name = 'nchc1' WHERE name = 'lab-a'", (self.a.user_id,))

    def client(self, who="alice"):
        if who not in self.clients:
            c = self.w.web()
            assert self.w.login(c, who).status_code == 303
            self.clients[who] = c
        return self.clients[who]

    def anon(self):
        return self.w.web()

    def area(self, who="alice"):
        return self.uploads / who

    def token(self, c):
        return upload_token(c.get("/upload").text)

    def post(self, c=None, files=((R1, b"AAAA"), (R2, b"CCCC")), *, ce="gcb1", name="ds1", version="v1", sheet=None, token=FETCH, query="", headers=None,
             extra=()):
        c = c or self.client()
        fields = []
        tok = self.token(c) if token is FETCH else token
        if tok is not None:
            fields.append(("csrf", tok))
        fields += [("ce", ce), ("name", name), ("version", version)] + list(extra)
        h = {"content-type": CTYPE}
        h.update(headers or {})
        return c.post("/upload" + query, content=multipart(fields, files, sheet), headers=h)

    def ok(self, c=None, **kw):
        r = self.post(c, **kw)
        assert r.status_code == 303, r.text
        m = re.fullmatch(r"/upload/([0-9a-f]{32})(\?lang=en)?", r.headers["location"])
        assert m, r.headers["location"]
        return m.group(1)

    # ---- what the database and the folder hold -----------------------------------------------------------------------------
    def jobs(self):
        return sql_rows(self.state, "SELECT * FROM jobs WHERE kind = 'put_upload' ORDER BY id")

    def finish(self, job_id, ok=True, message=None, path=None, size=None):
        row = sql_rows(self.state, "SELECT args_json FROM jobs WHERE id = ?", (job_id,))[0]
        args = json.loads(row["args_json"])
        result = {"ok": ok, "bytes": args["size"] if size is None else size, "path": args["dest"] if path is None else path}
        if message:
            result["message"] = message
        sql_exec(self.state, "UPDATE jobs SET state = 'done', result_json = ?, finished_at = ? WHERE id = ?", (json.dumps(result), time.time(), job_id))

    def claim(self, job_id):
        sql_exec(self.state, "UPDATE jobs SET state = 'claimed', claimed_at = ? WHERE id = ?", (time.time(), job_id))

    def expire(self, job_id):
        sql_exec(self.state, "UPDATE jobs SET state = 'expired', finished_at = ? WHERE id = ?", (time.time(), job_id))

    def record(self, batch, who="alice"):
        return json.loads((self.area(who) / ".batches" / (batch + ".json")).read_text(encoding="utf-8"))

    def listing(self, who="alice"):
        a = self.area(who)
        return sorted(p.name for p in a.iterdir()) if a.exists() else []

    def datasets(self, who="alice"):
        from abf_platform.actions import datasets
        caller = self.a if who == "alice" else self.b
        return datasets.list_datasets(self.state, caller=caller)["datasets"]

    def register_dataset(self, name="ds1", version="v1", who="alice", ce="gcb1", bucket="lab-bucket"):
        from abf_platform.actions import datasets
        url = "gs://%s/uploads/%s/x.fastq.gz" % (bucket, who)
        out = datasets.register_dataset(self.state, name=name, version=version, samplesheet="sample,fastq_1\ns1,%s\n" % url, files=[{"path": url}],
                                        caller=self.a if who == "alice" else self.b, destination=ce)
        assert out["ok"], out
        return out

    def confirmations(self):
        return sql_rows(self.state, "SELECT count(*) AS n FROM confirmations")[0]["n"]


@pytest.fixture
def up(tmp_path, monkeypatch):
    return Up(tmp_path, monkeypatch)


def middle(text):
    return plain(pane(text, "middle"))


# =============================================================================================================================
# User story 1 - GET /upload
# =============================================================================================================================
def form_of(text):
    m = re.search(r'<form class="lform" method="post" action="(/upload[^"]*)" enctype="multipart/form-data">(.*?)</form>', text, re.S)
    assert m, text[:2000]
    return m.group(1), m.group(2)


def test_tc001_the_form(up):
    # TC-001
    r = up.client().get("/upload")
    assert r.status_code == 200
    action, form = form_of(r.text)
    assert action == "/upload"
    assert re.search(r'<select name="ce"', form) and 'name="name"' in form and 'name="version"' in form
    assert re.search(r'<input type="file" name="fastq" multiple', form)
    assert re.search(r'<input type="file" name="samplesheet"(?![^>]*required)', form)
    assert re.search(r'<input type="hidden" name="csrf" value="[0-9a-f]+">', form)
    assert len(re.findall(r'<button type="submit">', form)) == 1


def test_tc002_environments_listed_exactly(up):
    # TC-002
    up.env("aws1", "aws-bucket", up.a, platform=AWS)
    _, form = form_of(up.client().get("/upload").text)
    assert sorted(re.findall(r'<option value="([^"]*)"', form)) == ["aws1", "gcb1"]


def test_tc003_an_environment_that_is_not_available_is_not_offered(up):
    # TC-003
    up.env("gcb-off", "off-bucket", up.a, status="invalid")
    _, form = form_of(up.client().get("/upload").text)
    assert re.findall(r'<option value="([^"]*)"', form) == ["gcb1"]


def test_tc004_a_slurm_environment_is_not_offered(up):
    # TC-004
    up.slurm_for_alice()
    _, form = form_of(up.client().get("/upload").text)
    assert re.findall(r'<option value="([^"]*)"', form) == ["gcb1"]


def test_tc005_somebody_elses_environment_is_nowhere_on_the_page(up):
    # TC-005
    r = up.client().get("/upload")
    assert "gcb2" not in r.text and "other-bucket" not in r.text
    assert "gcb2" not in up.client().get("/upload?lang=en").text


def test_tc006_no_usable_environment_is_one_sentence_and_a_link(up):
    # TC-006
    sql_exec(up.state, "UPDATE compute_envs SET status = 'invalid' WHERE name = 'gcb1'")
    r = up.client().get("/upload")
    assert r.status_code == 200
    m = pane(r.text, "middle")
    assert "沒有可用的雲端運算環境" in plain(m) and 'href="/settings"' in m
    assert "<form" not in m and 'type="file"' not in m and "<button" not in m
    up.slurm_for_alice()
    assert 'type="file"' not in pane(up.client().get("/upload").text, "middle")


def test_tc007_tc008_the_slurm_sentence_only_when_there_is_a_slurm_environment(up):
    # TC-008 first (alice has none), then TC-007
    assert "國網環境的資料目前請用指令上傳" not in up.client().get("/upload").text
    up.slurm_for_alice()
    zh = up.client().get("/upload").text
    assert "國網環境的資料目前請用指令上傳" in zh
    en = up.client().get("/upload?lang=en").text
    sentence = re.search(r"<p class=\"muted\">([^<]*Slurm[^<]*)</p>", en)
    assert sentence and not cjk(sentence.group(1))


def test_tc009_the_two_gigabyte_limit_is_written_and_is_the_real_one(up):
    # TC-009
    from abf_platform import uploads_web
    assert uploads_web.FILE_LIMIT == 2_000_000_000
    for q in ("", "?lang=en"):
        text = middle(up.client().get("/upload" + q).text)
        assert "2 GB" in text
    assert "更大的檔請改用指令" in middle(up.client().get("/upload").text)
    assert "larger" in middle(up.client().get("/upload?lang=en").text)


def test_tc010_a_big_file_command_per_environment(up):
    # TC-010
    from abf_platform import cloud_store, compute_envs
    up.env("aws1", "aws-bucket", up.a, platform=AWS)
    text = pane(up.client().get("/upload").text, "middle")
    import html as htmllib
    commands = {n: htmllib.unescape(c) for n, c in re.findall(r"<li><span class=\"muted\">([^<]*)</span> <code>([^<]*)</code></li>", text)}
    assert set(commands) == {"aws1", "gcb1"}
    assert commands["gcb1"].startswith("gcloud storage cp") and "gs://lab-bucket/uploads/alice/" in commands["gcb1"]
    assert commands["aws1"].startswith("aws s3 cp") and "s3://aws-bucket/uploads/alice/" in commands["aws1"]
    for name in ("gcb1", "aws1"):
        env = compute_envs.get(up.state, name, owner=up.a.user_id)
        assert commands[name] == cloud_store.big_file_command(env, "alice", cloud_store.workdir_scheme(env))
    assert "other-bucket" not in text and "uploads/bob" not in text


def test_tc011_required_markers_and_the_legend(up):
    # TC-011
    for q, title, legend in (("", "必填", "* 必填"), ("?lang=en", "Required", "* Required")):
        _, form = form_of(up.client().get("/upload" + q).text)
        labels = re.findall(r'<label>(.*?)</label>', form, re.S)
        assert len(labels) == 5
        marked = [bool(re.search(r'<span class="req" title="%s">\*</span>' % title, l)) for l in labels]
        assert marked == [True, True, True, True, False]
        assert legend in plain(pane(up.client().get("/upload" + q).text, "middle"))
        assert plain(form).count(title) == 0


def test_tc012_the_english_page_has_no_chinese(up):
    # TC-012
    text = pane(up.client().get("/upload?lang=en").text, "middle")
    text = re.sub(r"<code>[^<]*</code>", "", text)
    assert not cjk(plain(text))
    assert "Compute environment" in text and "Dataset name" in text


def test_tc013_the_button_is_a_fixed_verb(up):
    # TC-013
    for q, verb in (("", "上傳"), ("?lang=en", "Upload")):
        buttons = re.findall(r"<button[^>]*>(.*?)</button>", up.client().get("/upload" + q).text, re.S)
        assert verb in buttons
        assert not [b for b in buttons if re.search(r"\d|\.fastq|MB|GB", b)]


def test_tc014_a_page_without_a_login_goes_to_the_login_like_launch(up):
    # TC-014
    c = up.anon()
    a, b = c.get("/upload"), c.get("/launch")
    assert (a.status_code, a.headers["location"]) == (b.status_code, b.headers["location"]) and a.status_code == 303
    assert "<form" not in a.text


def test_tc015_a_temporary_password_login_is_sent_to_welcome(up):
    # TC-015
    from test_temp_password import login_temp
    up.w.user("ann")
    c, r, _ = login_temp(up.w)
    before = len(up.jobs())
    g = c.get("/upload")
    p = c.post("/upload", content=multipart([("csrf", "x"), ("ce", "gcb1"), ("name", "n"), ("version", "v")], [(R1, b"A"), (R2, b"C")]),
               headers={"content-type": CTYPE})
    assert (g.status_code, g.headers["location"]) == (303, "/welcome") and (p.status_code, p.headers["location"]) == (303, "/welcome")
    assert len(up.jobs()) == before and up.listing("ann") == []


def test_tc016_no_style_attribute_no_script_no_outside_address_and_the_launch_csp(up):
    # TC-016
    c = up.client()
    batch = up.ok(c)
    pages = [c.get("/upload"), c.get("/upload/" + batch), c.get("/upload?lang=en")]
    launch = c.get("/launch")
    for r in pages:
        assert not re.search(r"\sstyle\s*=", r.text) and "<script" not in r.text.lower()
        assert not re.search(r'(?:src|href|action)="(?!/)[^"]*"', r.text), re.findall(r'(?:src|href|action)="(?!/)[^"]*"', r.text)
        assert "<link" not in r.text and re.search(r"<style>(.*?)</style>", r.text, re.S).group(1) == style_of(launch.text)
        assert r.headers["content-security-policy"] == launch.headers["content-security-policy"]
        assert 'class="drop' not in r.text and "dropzone" not in r.text.lower()


def test_tc017_tc018_words_of_the_pages(up):
    # TC-017, TC-018: no word of the banned list, and nothing of the machine, in any page this task writes (own sentences only)
    c = up.client()
    texts = [middle(c.get("/upload").text), middle(c.get("/upload?lang=en").text)]
    texts.append(middle(up.post(c, files=((R1, b""), (R2, b"C"))).text))                         # 400
    texts.append(middle(up.post(c, files=(("../x_R1.fastq.gz", b"A"),)).text))                    # 400 name
    texts.append(middle(up.post(c, files=((R1, b"A"), (R1, b"A"))).text))                         # 400 twice
    texts.append(middle(up.post(c, files=((R1, b"A"), ("b_R1.fastq.gz", b"A"))).text))           # 400 unpaired
    texts.append(middle(up.post(c, files=(), ).text))                                             # 400 none
    texts.append(middle(up.post(c, name="").text))                                                # 400 field
    batch = up.ok(c)
    texts.append(middle(c.get("/upload/" + batch).text))
    first, second = [j["id"] for j in up.jobs()]
    up.finish(first, ok=False, message="cloud size differs")
    up.expire(second)
    texts.append(middle(c.get("/upload/" + batch).text))
    texts.append(middle(c.get("/upload/" + batch + "?lang=en").text))
    for text in texts:
        for word in BANNED:
            assert word not in text, (word, text)
        for word in SECRET_WORDS:
            assert word not in text, (word, text)
        assert str(up.uploads) not in text


def test_tc019_the_new_files_keep_no_list_of_cloud_types():
    # TC-019
    for name in ("web_upload.py", "uploads_web.py", "actions/uploads.py"):
        src = (PKG / name).read_text(encoding="utf-8")
        assert "GOOGLE_BATCH" not in src and "AWS" not in src and "googlebatch" not in src and "awsbatch" not in src, name
    assert "CLOUD_JOB_KINDS" in (PKG / "web_upload.py").read_text(encoding="utf-8") + (PKG / "actions" / "uploads.py").read_text(encoding="utf-8")


# =============================================================================================================================
# User story 2 - POST /upload
# =============================================================================================================================
def only_files(up, who="alice"):
    """What stands in the person's upload folder apart from the hidden folders (.batches) and the staging folders."""
    return [n for n in up.listing(who) if not n.startswith(".")]


def nothing_left(up, who="alice"):
    return [n for n in up.listing(who) if n.startswith(".incoming-")] == []


def test_tc020_one_press_does_it_all(up):
    # TC-020
    c = up.client()
    r = up.post(c)
    assert r.status_code == 303 and re.fullmatch(r"/upload/[0-9a-f]{32}", r.headers["location"])


def test_tc021_the_files_are_staged_in_the_upload_folder(up):
    # TC-021
    up.ok()
    assert (up.area() / R1).read_bytes() == b"AAAA" and (up.area() / R2).read_bytes() == b"CCCC"
    assert nothing_left(up) and sorted(only_files(up)) == [R1, R2]


class Counting:
    """An async stream in pieces that keeps what the reader has taken, and runs a check after each piece."""

    def __init__(self, data, piece, check=None):
        self.data, self.piece, self.check, self.taken = data, piece, check, 0

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for i in range(0, len(self.data), self.piece):
            chunk = self.data[i:i + self.piece]
            self.taken += len(chunk)
            yield chunk
            if self.check:
                self.check(self.taken)
        yield b""


def test_tc022_bytes_land_in_the_staging_folder_and_move_only_when_done(up, tmp_path):
    # TC-022
    from abf_platform import uploads_web
    area = up.area()
    area.mkdir(parents=True, exist_ok=True)
    incoming = uploads_web.incoming_for(area, "a" * 32)
    data = multipart([("csrf", "x")], [(R1, os.urandom(3000)), (R2, os.urandom(3000))])
    seen = []

    def check(taken):
        if taken >= len(data) // 2 and not seen:
            staged = list(Path(incoming).glob("*"))
            seen.append((sum(p.stat().st_size for p in staged), [n for n in os.listdir(area) if not n.startswith(".")]))

    got = asyncio.run(uploads_web.receive(Counting(data, 500, check), CTYPE, incoming))
    assert seen and seen[0][0] > 0 and seen[0][1] == []
    assert [f["size"] for f in got["files"]] == [3000, 3000] and all(Path(f["tmp"]).parent == Path(incoming) for f in got["files"])


def test_tc023_two_jobs_with_the_places(up):
    # TC-023
    up.ok()
    rows = up.jobs()
    assert len(rows) == 2
    args = [json.loads(r["args_json"]) for r in rows]
    assert [a["name"] for a in args] == [R1, R2] and {a["owner"] for a in args} == {"alice"} and {r["compute_env"] for r in rows} == {"gcb1"}
    assert [a["dest"] for a in args] == ["gs://lab-bucket/uploads/alice/" + n for n in (R1, R2)]


def test_tc024_no_confirmation_page(up):
    # TC-024
    before = up.confirmations()
    r = up.post()
    assert r.status_code == 303 and "/c/" not in r.headers["location"]
    assert up.confirmations() == before


def test_tc025_tc026_the_batch_record(up):
    # TC-025, TC-026
    batch = up.ok()
    rec = up.record(batch)
    assert (rec["batch"], rec["owner"], rec["ce"], rec["name"], rec["version"], rec["registered"]) == (batch, "alice", "gcb1", "ds1", "v1", False)
    assert [(f["name"], f["dest"]) for f in rec["files"]] == [(n, "gs://lab-bucket/uploads/alice/" + n) for n in (R1, R2)]
    assert [f["job_id"] for f in rec["files"]] == [j["id"] for j in up.jobs()] and rec["samplesheet"]
    text = json.dumps(rec)
    for secret in ("password", "cookie", "csrf", "token"):
        assert secret not in text.lower()
    path = up.area() / ".batches" / (batch + ".json")
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert [p.name for p in path.parent.iterdir()] == [batch + ".json"]
    assert not any("batch" in r["name"] for r in sql_rows(up.state, "SELECT name FROM sqlite_master WHERE type = 'table'"))


def test_tc027_the_sheet_is_made_from_the_pairs(up):
    # TC-027
    rec = up.record(up.ok())
    assert rec["samplesheet"].strip().splitlines() == ["sample,fastq_1,fastq_2", "sampleA,%s,%s" % (R1, R2)]


def test_tc028_the_sheet_the_person_gave_is_kept_as_it_is(up):
    # TC-028
    given = "sample,fastq_1,fastq_2,note\nx,%s,%s,hello\n" % (R1, R2)
    assert up.record(up.ok(sheet=given))["samplesheet"] == given


def test_tc029_one_file_with_its_own_sheet(up):
    # TC-029
    up.ok(files=(("solo.fastq.gz", b"AAAA"),), sheet="sample,fastq_1\nsolo,solo.fastq.gz\n")
    assert len(up.jobs()) == 1


def test_tc030_an_aws_environment(up):
    # TC-030
    up.env("aws1", "aws-bucket", up.a, platform=AWS)
    up.ok(ce="aws1")
    assert [json.loads(j["args_json"])["dest"] for j in up.jobs()] == ["s3://aws-bucket/uploads/alice/" + n for n in (R1, R2)]


def test_tc031_a_body_over_the_form_limit_is_not_cut(up):
    # TC-031
    data = os.urandom(1024 * 1024)
    up.ok(files=((R1, data), (R2, b"CCCC")))
    assert (up.area() / R1).read_bytes() == data


def test_tc032_the_form_limit_of_the_other_routes_is_unchanged(up):
    # TC-032
    from abf_platform import web
    assert web.MAX_BODY == 16384
    c = up.anon()
    pad = "x" * 20000
    r = c.post("/login", content=("pad=%s&name=alice&password=%s" % (pad, "correct horse battery")).encode(),
               headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 401


def test_tc033_exactly_the_limit_is_taken(up, monkeypatch):
    # TC-033
    from abf_platform import uploads_web
    monkeypatch.setattr(uploads_web, "FILE_LIMIT", 40)
    up.ok(files=((R1, b"A" * 40), (R2, b"C" * 40)))


def test_tc034_tc036_one_byte_over_stops_it_and_cleans_the_whole_batch(up, monkeypatch):
    # TC-034, TC-036
    from abf_platform import uploads_web
    monkeypatch.setattr(uploads_web, "FILE_LIMIT", 40)
    before = up.listing()
    r = up.post(files=((R1, b"A" * 40), (R2, b"C" * 41)))
    assert r.status_code == 413
    assert R2 in plain(pane(r.text, "middle"))
    assert up.listing() == before and up.jobs() == [] and not (up.area() / ".batches").exists()


def test_tc035_the_read_stops_at_the_limit():
    # TC-035
    import tempfile
    from abf_platform import uploads_web
    limit = 5000
    data = multipart([("csrf", "x")], [(R1, b"A" * (limit * 100))])
    stream = Counting(data, 1000)
    with tempfile.TemporaryDirectory() as tmp:
        incoming = os.path.join(tmp, ".incoming-" + "b" * 32)
        with pytest.raises(uploads_web.Rejected) as e:
            asyncio.run(uploads_web.receive(stream, CTYPE, incoming, limit=limit))
        assert e.value.code == 413 and not os.path.exists(incoming)
    assert stream.taken < limit + 3000 < len(data) / 20


def test_tc037_the_413_page_has_the_limit_and_the_command(up, monkeypatch):
    # TC-037
    from abf_platform import uploads_web
    monkeypatch.setattr(uploads_web, "FILE_LIMIT", 10)
    r = up.post(files=((R1, b"A" * 11),))
    text = pane(r.text, "middle")
    assert "2 GB" in plain(text) and "gcloud storage cp" in text and "gs://lab-bucket/uploads/alice/" in text
    assert "other-bucket" not in text and "uploads/bob" not in text


def test_tc038_an_empty_file_is_refused(up):
    # TC-038
    r = up.post(files=((R1, b""), (R2, b"C")))
    assert r.status_code == 400 and R1 in plain(pane(r.text, "middle")) and "空" in plain(pane(r.text, "middle"))
    assert up.jobs() == [] and only_files(up) == [] and nothing_left(up)


@pytest.mark.parametrize("tc,bad", [("039", "../evil_R1.fastq.gz"), ("040", "a/b_R1.fastq.gz"), ("041", "a\\b_R1.fastq.gz"), ("042", "a..b_R1.fastq.gz"),
                                    ("043", b"bad\x01name_R1.fastq.gz")])
def test_tc039_to_043_a_bad_name_is_refused_whole(up, tc, bad):
    # TC-039 ../ ; TC-040 / ; TC-041 \ ; TC-042 .. ; TC-043 a control character
    r = up.post(files=((bad, b"AAAA"), (R2, b"CCCC")))
    assert r.status_code == 400
    assert up.jobs() == [] and nothing_left(up) and not (up.area() / ".batches").exists()
    names = [p.name for p in up.uploads.rglob("*")]
    assert not [n for n in names if n.endswith("_R1.fastq.gz") or n == R2]


def test_tc044_the_same_name_twice_in_a_batch(up):
    # TC-044
    r = up.post(files=((R1, b"A"), (R1, b"B"), (R2, b"C")))
    assert r.status_code == 400 and R1 in plain(pane(r.text, "middle")) and up.jobs() == [] and nothing_left(up) and only_files(up) == []


IN_USE = "此檔名正在上傳或已使用，請改檔名。"


def test_tc045_a_name_that_is_in_the_folder_is_refused(up):
    # TC-045
    up.area().mkdir(parents=True, exist_ok=True)
    (up.area() / R1).write_bytes(b"OLD")
    r = up.post()
    assert r.status_code == 400 and IN_USE in plain(pane(r.text, "middle"))
    assert (up.area() / R1).read_bytes() == b"OLD" and up.jobs() == [] and nothing_left(up)
    en = up.post(query="?lang=en")
    assert "This file name is in use by another upload; rename the file." in plain(pane(en.text, "middle"))


def test_tc046_a_failed_batch_gives_its_names_back(up):
    # TC-046
    c = up.client()
    old = up.ok(c, files=((R1, b"OLD1"),), sheet="sample,fastq_1\nA,%s\n" % R1)
    up.finish(up.jobs()[0]["id"], ok=False, message="cloud size differs")
    new = up.ok(c, files=((R1, b"NEW1"),), sheet="sample,fastq_1\nA,%s\n" % R1, version="v2")
    assert (up.area() / R1).read_bytes() == b"NEW1"
    assert up.record(old)["superseded"] is True and up.record(new)["superseded"] is False and len(up.jobs()) == 2


def test_tc047_a_running_batch_keeps_its_names(up):
    # TC-047
    c = up.client()
    old = up.ok(c)
    for state in ("queued", "claimed"):
        if state == "claimed":
            for j in up.jobs():
                up.claim(j["id"])
        r = up.post(c, version="v2")
        assert r.status_code == 400 and IN_USE in plain(pane(r.text, "middle"))
    assert (up.area() / R1).read_bytes() == b"AAAA" and up.record(old)["superseded"] is False and len(up.jobs()) == 2


def test_tc048_a_registered_batch_keeps_its_names(up):
    # TC-048
    c = up.client()
    batch = up.ok(c)
    for j in up.jobs():
        up.finish(j["id"])
    assert "已登記" in c.get("/upload/" + batch).text
    r = up.post(c, version="v2")
    assert r.status_code == 400 and IN_USE in plain(pane(r.text, "middle")) and (up.area() / R1).read_bytes() == b"AAAA"


def test_tc049_the_same_name_for_another_person(up):
    # TC-049
    up.ok()
    up.ok(up.client("bob"), ce="gcb2")
    assert (up.area() / R1).read_bytes() == b"AAAA" and (up.area("bob") / R1).read_bytes() == b"AAAA"


def test_tc050_tc051_the_name_and_version_are_already_there(up):
    # TC-050, TC-051
    up.register_dataset()
    before = up.listing()
    r = up.post()
    assert r.status_code == 400 and "此名稱與版本已登記，請換一個版本。" in plain(pane(r.text, "middle"))
    assert up.listing() == before and up.jobs() == []
    en = up.post(query="?lang=en")
    assert en.status_code == 400 and "This name and version are already registered. Use another version." in plain(pane(en.text, "middle"))


def test_tc052_the_same_name_of_another_person_is_not_in_the_way(up):
    # TC-052
    up.register_dataset(who="bob", ce="gcb2", bucket="other-bucket")
    up.ok()


def test_tc053_to_tc055_empty_fields(up):
    # TC-053 no file, TC-054 no name, TC-055 no version
    r = up.post(files=())
    assert r.status_code == 400 and "請選擇至少一個 FASTQ 檔。" in plain(pane(r.text, "middle"))
    assert "Choose at least one FASTQ file." in plain(pane(up.post(files=(), query="?lang=en").text, "middle"))
    for key, title in (("name", "資料集名稱"), ("version", "版本")):
        r = up.post(**{key: ""})
        assert r.status_code == 400
        label = re.search(r'<label><span class="lbl">%s <span[^>]*>\*</span></span><input name="%s"[^>]*>(.*?)</label>' % (title, key), r.text, re.S)
        assert label and "此欄為必填。" in label.group(1)
        assert "This field is required." in plain(up.post(query="?lang=en", **{key: ""}).text)
    assert up.jobs() == [] and only_files(up) == [] and nothing_left(up) and not (up.area() / ".batches").exists()


def test_tc056_the_rule_for_name_and_version(up):
    # TC-056
    for kw in ({"name": "bad name!"}, {"version": "v" * 65}):
        r = up.post(**kw)
        assert r.status_code == 400 and "只能用英數字與 . _ -，長度 1 到 64。" in plain(pane(r.text, "middle"))
        assert up.jobs() == [] and only_files(up) == [] and nothing_left(up)


def test_tc057_a_sheet_over_one_mib(up):
    # TC-057
    r = up.post(sheet="sample,fastq_1\n" + "x" * (1024 * 1024 + 10))
    assert r.status_code == 400 and "1 MiB" in plain(pane(r.text, "middle")) and up.jobs() == [] and nothing_left(up) and only_files(up) == []


def test_tc058_files_that_cannot_be_paired_are_named(up):
    # TC-058
    r = up.post(files=((R1, b"A"), ("sampleB_R1.fastq.gz", b"B")))
    text = plain(pane(r.text, "middle"))
    assert r.status_code == 400 and R1 in text and "sampleB_R1.fastq.gz" in text
    assert up.jobs() == [] and nothing_left(up) and only_files(up) == []


@pytest.mark.parametrize("tc,sheet,word", [("059", "sample,reads\nA,%s\n" % R1, "fastq_1"), ("060", "sample,fastq_1\nA,other.fastq.gz\n", "不在登記的檔案內"),
                                           ("061", "sample,fastq_1\nA,https://example.org/x.fastq.gz\n", "網址"),
                                           ("062", "sample,fastq_1,note\nA,%s,%s\n" % (R1, AKID), "憑證")])
def test_tc059_to_tc062_a_bad_sheet(up, tc, sheet, word):
    # TC-059 missing column; TC-060 a cell not in the batch; TC-061 a URL; TC-062 something that looks like a credential (never shown back)
    r = up.post(files=((R1, b"A"),), sheet=sheet)
    text = plain(pane(r.text, "middle"))
    assert r.status_code == 400 and word in text
    assert AKID not in r.text and "example.org" not in r.text
    assert up.jobs() == [] and nothing_left(up) and only_files(up) == [] and not (up.area() / ".batches").exists()


def test_tc063_a_job_refused_half_way(up, monkeypatch):
    # TC-063, TC-096
    from abf_platform import jobs
    real, calls = jobs.enqueue_put_upload, []

    def flaky(*a, **kw):
        calls.append(a[4])
        if len(calls) == 2:
            raise jobs.JobRefused("agent ag-gcb1 is offline (代理離線); nothing was queued")
        return real(*a, **kw)

    monkeypatch.setattr(jobs, "enqueue_put_upload", flaky)
    c = up.client()
    batch = up.ok(c)
    assert len(up.jobs()) == 1 and (up.area() / R1).exists() and not (up.area() / R2).exists() and nothing_left(up)
    page = pane(c.get("/upload/" + batch).text, "middle")
    rows = dict(re.findall(r"<tr><td>([^<]*)</td><td>[^<]*</td><td>(.*?)</td></tr>", page, re.S))
    assert "○ 排隊中" in rows[R1] and "✕ 失敗" in rows[R2]
    assert "代理離線" in rows[R2]
    assert up.datasets() == [] and up.record(batch)["registered"] is False
    up.finish(up.jobs()[0]["id"])
    again = c.get("/upload/" + batch)
    assert "已登記，前往送出" not in again.text and up.datasets() == []


def test_tc064_an_environment_that_is_not_yours_or_not_there(up):
    # TC-064
    up.env("gcb-off", "off-bucket", up.a, status="invalid")
    c = up.client()
    others = up.post(c, ce="gcb2"), up.post(c, ce="no-such"), up.post(c, ce="gcb-off")
    assert all(400 <= r.status_code < 500 for r in others)
    assert others[0].text == others[1].text
    assert up.jobs() == [] and only_files(up) == [] and nothing_left(up)


def test_tc065_tc066_a_wrong_token(up):
    # TC-065 none or wrong; TC-066 a token made for another purpose
    c = up.client()
    cookie = c.cookies.get("abf_web")
    for tok in (None, "wrong", c.app.state.csrf_token(cookie, "logout"), c.app.state.csrf_token(cookie, "welcome")):
        r = up.post(c, token=tok)
        assert r.status_code == 403, tok
    assert up.jobs() == [] and only_files(up) == [] and nothing_left(up) and not (up.area() / ".batches").exists()


def test_tc065_a_token_that_comes_after_the_files_writes_nothing(up):
    # TC-065 (the token is missing before the first file: nothing is written)
    c = up.client()
    body = multipart([("ce", "gcb1"), ("name", "ds1"), ("version", "v1")], [(R1, b"A"), (R2, b"C")])
    r = c.post("/upload", content=body, headers={"content-type": CTYPE})
    assert r.status_code == 403 and up.jobs() == [] and only_files(up) == [] and nothing_left(up)


def test_tc067_another_origin(up):
    # TC-067
    r = up.post(headers={"origin": "https://evil.example"})
    assert r.status_code == 403 and up.jobs() == [] and only_files(up) == [] and nothing_left(up)
    assert up.post(headers={"referer": "https://evil.example/x"}).status_code == 403


def test_tc068_tc069_nobody_logged_in(up):
    # TC-068, TC-069
    c = up.anon()
    launch = c.post("/launch", data={"x": "y"})
    for headers in ({}, {"authorization": "Bearer abf_pat_" + "a1B2c3D4e5" * 3}):
        r = c.post("/upload", content=multipart([("csrf", "x"), ("ce", "gcb1"), ("name", "n"), ("version", "v")], [(R1, b"A")]),
                   headers=dict({"content-type": CTYPE}, **headers))
        assert (r.status_code, r.headers["location"]) == (launch.status_code, launch.headers["location"]) == (303, "/login")
    assert up.jobs() == [] and up.listing() == []


def test_tc070_a_disk_error_is_a_plain_page(up, monkeypatch):
    # TC-070
    from abf_platform import uploads_web

    def boom(handle, data):
        raise OSError(28, "No space left on device: /srv/secret/place")

    monkeypatch.setattr(uploads_web, "_write", boom)
    r = up.post()
    assert r.status_code >= 400 and "伺服器暫時無法收下檔案" in plain(pane(r.text, "middle"))
    for word in ("Traceback", "/srv/secret", "No space", "sqlite"):
        assert word not in r.text
    assert up.jobs() == [] and only_files(up) == [] and nothing_left(up)


# =============================================================================================================================
# User story 3 - GET /upload/{batch} and the registering
# =============================================================================================================================
def rows_of(text):
    """{file name: (size text, state cell html)} from the progress table."""
    return {n: (s, st) for n, s, st in re.findall(r"<tr><td>([^<]*)</td><td>([^<]*)</td><td>(.*?)</td></tr>", pane(text, "middle"), re.S)}


def four_files(up, c=None):
    names = ["s%d.fastq.gz" % i for i in range(1, 5)]
    sheet = "sample,fastq_1\n" + "".join("s%d,%s\n" % (i, n) for i, n in enumerate(names, 1))
    batch = up.ok(c, files=tuple((n, b"AAAA") for n in names), sheet=sheet)
    return batch, names


def test_tc071_one_row_per_file(up):
    # TC-071
    c = up.client()
    batch = up.ok(c, files=((R1, b"A" * 1500), (R2, b"CCCC")))
    rows = rows_of(c.get("/upload/" + batch).text)
    assert list(rows) == [R1, R2] and rows[R1][0] == "1.5 KB" and rows[R2][0] == "4 B"


def test_tc072_to_tc077_each_state_is_a_symbol_and_a_word(up):
    # TC-072 queued, TC-073 sending, TC-074 done, TC-075 failed with the message, TC-076 expired, TC-077 English
    c = up.client()
    batch, names = four_files(up, c)
    ids = [j["id"] for j in up.jobs()]
    up.claim(ids[1])
    up.finish(ids[2])
    up.finish(ids[3], ok=False, message="cloud size differs")
    zh = rows_of(c.get("/upload/" + batch).text)
    assert "○ 排隊中" in zh[names[0]][1] and "◐ 傳送中" in zh[names[1]][1] and "✓ 完成" in zh[names[2]][1]
    assert "✕ 失敗" in zh[names[3]][1] and "cloud size differs" in zh[names[3]][1]
    en = rows_of(c.get("/upload/%s?lang=en" % batch).text)
    assert "○ Queued" in en[names[0]][1] and "◐ Sending" in en[names[1]][1] and "✓ Done" in en[names[2]][1] and "✕ Failed" in en[names[3]][1]
    up.expire(ids[0])
    again = rows_of(c.get("/upload/" + batch).text)
    assert "✕ 失敗" in again[names[0]][1] and "逾時" in again[names[0]][1]
    for cell, klass in ((zh[names[0]][1], "state-unknown"), (zh[names[1]][1], "state-running"), (zh[names[2]][1], "state-succeeded"), (zh[names[3]][1], "state-failed")):
        assert klass in cell


def test_tc078_it_reloads_itself_while_files_are_on_the_way(up):
    # TC-078
    c = up.client()
    batch = up.ok(c)
    page = c.get("/upload/" + batch).text
    assert '<meta http-equiv="refresh" content="15">' in page and "<script" not in page
    for j in up.jobs():
        up.finish(j["id"])
    assert "refresh" not in c.get("/upload/" + batch).text


def finish_all(up):
    for j in up.jobs():
        up.finish(j["id"])


def test_tc079_tc080_when_everything_is_in_the_dataset_is_kept(up):
    # TC-079, TC-080
    from abf_platform.actions import datasets
    c = up.client()
    batch = up.ok(c)
    assert up.datasets() == []
    finish_all(up)
    c.get("/upload/" + batch)
    assert [(d["name"], d["version"], d["n_files"]) for d in up.datasets()] == [("ds1", "v1", 2)]
    got = datasets.get_dataset(up.state, "ds1", "v1", caller=up.a)
    places = ["gs://lab-bucket/uploads/alice/" + n for n in (R1, R2)]
    assert [f["path"] for f in got["files"]] == places
    assert got["samplesheet"].strip().splitlines() == ["sample,fastq_1,fastq_2", "sampleA,%s,%s" % tuple(places)]
    assert up.record(batch)["registered"] is True


def test_tc081_an_aws_dataset_is_in_s3_places(up):
    # TC-081
    from abf_platform.actions import datasets
    up.env("aws1", "aws-bucket", up.a, platform=AWS)
    c = up.client()
    batch = up.ok(c, ce="aws1")
    finish_all(up)
    c.get("/upload/" + batch)
    got = datasets.get_dataset(up.state, "ds1", "v1", caller=up.a)
    assert [f["path"] for f in got["files"]] == ["s3://aws-bucket/uploads/alice/" + n for n in (R1, R2)] and "s3://aws-bucket/uploads/alice/" + R1 in got["samplesheet"]


def test_tc082_registered_go_to_launch(up):
    # TC-082
    c = up.client()
    batch = up.ok(c)
    finish_all(up)
    zh = c.get("/upload/" + batch).text
    assert "已登記，前往送出" in zh and re.search(r'<a href="/launch">已登記，前往送出</a>', zh)
    en = c.get("/upload/%s?lang=en" % batch).text
    assert "Registered" in en and re.search(r'<a href="/launch\?lang=en">Registered, go to launch</a>', en)


def test_tc083_the_new_dataset_is_a_choice_at_step_four(up):
    # TC-083
    c = up.client()
    batch = up.ok(c)
    assert "datasets/ds1/v1.csv" not in c.get("/launch").text
    finish_all(up)
    c.get("/upload/" + batch)
    step4 = c.get("/launch").text
    assert '<option value="datasets/ds1/v1.csv"' in step4
    assert (up.area() / "datasets" / "ds1" / "v1.csv").read_text(encoding="utf-8").count("gs://lab-bucket/uploads/alice/") == 2


def test_tc084_reloading_registers_once(up):
    # TC-084
    c = up.client()
    batch = up.ok(c)
    finish_all(up)
    pages = [c.get("/upload/" + batch) for _ in range(3)]
    assert [d["name"] for d in up.datasets()] == ["ds1"]
    assert all(p.status_code == 200 and "已登記，前往送出" in p.text and "已存在" not in p.text for p in pages)


def test_tc085_a_file_still_on_the_way_registers_nothing(up):
    # TC-085
    c = up.client()
    batch = up.ok(c)
    ids = [j["id"] for j in up.jobs()]
    up.finish(ids[0])
    up.claim(ids[1])
    page = c.get("/upload/" + batch).text
    assert up.datasets() == [] and "已登記，前往送出" not in page and "refresh" in page


def test_tc086_tc087_one_failure_registers_nothing_and_the_names_can_be_used_again(up):
    # TC-086, TC-087
    c = up.client()
    old = up.ok(c)
    ids = [j["id"] for j in up.jobs()]
    up.finish(ids[0])
    up.finish(ids[1], ok=False, message="cloud size differs")
    page = c.get("/upload/" + old).text
    assert up.datasets() == [] and "cloud size differs" in page and re.search(r'<a href="/upload">重新上傳</a>', page)
    new = up.ok(c, version="v2")
    assert up.record(old)["superseded"] is True
    for j in up.jobs()[2:]:
        up.finish(j["id"])
    c.get("/upload/" + new)
    assert [(d["name"], d["version"]) for d in up.datasets()] == [("ds1", "v2")]


def test_tc088_to_tc090_a_refused_registering_keeps_the_places_and_deletes_nothing(up):
    # TC-088, TC-089, TC-090
    c = up.client()
    batch = up.ok(c)
    finish_all(up)
    up.register_dataset("ds1", "v1")
    jobs_before = sql_rows(up.state, "SELECT count(*) AS n FROM jobs")[0]["n"]
    page = c.get("/upload/" + batch)
    text = plain(pane(page.text, "middle"))
    assert "已存在" in text and "檔案仍在您的雲端資料夾，可換一個版本重新上傳" in text
    assert "gs://lab-bucket/uploads/alice/" + R1 in text and "gs://lab-bucket/uploads/alice/" + R2 in text and "已登記，前往送出" not in page.text
    en = plain(pane(c.get("/upload/%s?lang=en" % batch).text, "middle"))
    assert "The files are still in your cloud folder" in en
    assert up.record(batch)["registered"] is False
    assert sql_rows(up.state, "SELECT count(*) AS n FROM jobs")[0]["n"] == jobs_before and {j["kind"] for j in sql_rows(up.state, "SELECT kind FROM jobs")} <= {"put_upload", "preflight"}
    assert [f["dest"] for f in up.record(batch)["files"]] == ["gs://lab-bucket/uploads/alice/" + n for n in (R1, R2)]


def test_tc091_tc092_tc093_a_batch_of_somebody_else_is_not_there(up):
    # TC-091, TC-092, TC-093
    batch = up.ok()
    finish_all(up)
    bob = up.client("bob")
    mine = bob.get("/upload/" + batch)
    assert mine.status_code == 404 and R1 not in mine.text and "ds1" not in mine.text and "gcb1" not in mine.text
    assert up.datasets() == [] and up.record(batch)["registered"] is False
    missing = bob.get("/upload/" + "0" * 32)
    assert missing.status_code == 404 and missing.text == mine.text
    for odd in ("nope", "..%2F..%2Fetc", "%2e%2e", "x" * 300):
        r = up.client().get("/upload/" + odd)
        assert r.status_code == 404 and str(up.uploads) not in r.text and "Traceback" not in r.text
    assert up.client().get("/upload/nope").text == mine.text.replace("bob", "alice")
    up.client().get("/upload/" + batch)
    assert len(up.datasets()) == 1


def test_tc094_the_progress_page_needs_a_login(up):
    # TC-094
    c = up.anon()
    a, b = c.get("/upload/" + "0" * 32), c.get("/launch")
    assert (a.status_code, a.headers["location"]) == (b.status_code, b.headers["location"]) == (303, "/login")
    from test_temp_password import login_temp
    up.w.user("ann")
    t, _, _ = login_temp(up.w)
    r = t.get("/upload/" + "0" * 32)
    assert (r.status_code, r.headers["location"]) == (303, "/welcome")


def test_tc095_the_platform_does_not_touch_the_staged_files(up):
    # TC-095
    c = up.client()
    batch = up.ok(c)
    finish_all(up)
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in up.area().iterdir() if p.is_file()}
    for _ in range(3):
        c.get("/upload/" + batch)
    after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in up.area().iterdir() if p.is_file()}
    assert before == after and set(before) == {R1, R2}


# =============================================================================================================================
# User story 4 - the way in
# =============================================================================================================================
def test_tc097_tc098_the_upload_button_is_a_link(up):
    # TC-097, TC-098
    c = up.client()
    left = pane(c.get("/").text, "left")
    assert '<a class="nv" href="/upload">↑ 上傳資料</a>' in left
    en = pane(c.get("/?lang=en").text, "left")
    assert '<a class="nv" href="/upload?lang=en">↑ Upload data</a>' in en
    assert not re.search(r'<span class="off">↑', left + en)


def test_tc099_the_rest_of_the_left_column_is_as_before(up):
    # TC-099
    left = pane(up.client().get("/").text, "left")
    assert '<a class="nv" href="/settings">設定</a>' in left
    for word in ("＋ 新專案", "搜尋專案或分析", "資料瀏覽", "儀表板"):
        assert re.search(r'<span class="off">%s <span class="later">之後開放</span></span>' % word, left), word


def test_tc100_step_four_with_no_sheet_points_to_the_upload_page(up):
    # TC-100
    c = up.client()
    for q, sentence in (("", "尚無已上傳的樣本表，請先上傳。"), ("?lang=en", "No samplesheet has been uploaded. Please upload one first.")):
        text = c.get("/launch" + q).text
        i = text.index(sentence)
        assert re.search(r'<a href="/upload%s">' % re.escape("?lang=en" if q else ""), text[i:i + 400])


# =============================================================================================================================
# User story 5 - layers, documents, the pinned tests
# =============================================================================================================================
def source(name):
    return (PKG / name).read_text(encoding="utf-8")


def function_source(path, names):
    src = (PKG / path).read_text(encoding="utf-8")
    tree = ast.parse(src)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            out.append(ast.get_source_segment(src, node))
    assert len(out) == len(names), names
    return "\n".join(out)


LAYER_WORDS = ("register_dataset", "draft_samplesheet", "check_web_upload", "pair_fastq", "actions.datasets", "get_dataset")


def test_tc106_the_web_files_do_not_speak_of_datasets():
    # TC-106
    for name in ("web.py", "web_board.py", "web_upload.py", "uploads_web.py"):
        for word in LAYER_WORDS:
            assert word not in source(name), (name, word)
    mine = function_source("actions/__init__.py", {"start_upload_batch", "upload_batch_status"})
    for word in LAYER_WORDS:
        assert word not in mine, word


def test_tc107_the_routes_only_call_the_two_actions():
    # TC-107
    from test_web_parity import called_actions
    handlers = function_source("web.py", {"upload_get", "upload_post", "upload_batch_get", "upload_page", "upload_envs"})
    assert called_actions(handlers) <= {"Caller", "list_compute_envs", "caller_area", "start_upload_batch", "upload_batch_status"}
    assert {"start_upload_batch", "upload_batch_status"} <= called_actions(handlers)
    for fn in ("start_upload_batch", "upload_batch_status"):
        body = function_source("actions/__init__.py", {fn})
        assert body.count("_uploads.") == 1 and "return _uploads." in body
    callers = sorted(str(p.relative_to(PKG)).replace("\\", "/") for p in PKG.rglob("*.py") if "enqueue_put_upload" in p.read_text(encoding="utf-8"))
    assert callers == ["actions/uploads.py", "jobs.py"]
    assert [str(p.relative_to(PKG)).replace("\\", "/") for p in PKG.rglob("*.py")
            if "register_dataset(" in p.read_text(encoding="utf-8") and p.name in ("uploads.py", "web.py", "web_upload.py", "uploads_web.py")] == ["actions/uploads.py"]


def test_tc120_check_samplesheet_writes_and_opens_nothing(up, monkeypatch):
    # TC-120
    from abf_platform import store
    from abf_platform.actions import datasets
    before = len(up.datasets())

    def boom(*a, **k):
        raise AssertionError("the database was touched")

    monkeypatch.setattr(store, "connect_state", boom)
    monkeypatch.setattr(store, "open_readonly", boom)
    good = datasets.check_samplesheet("sample,fastq_1\nA,x.fastq.gz\n", {"x.fastq.gz"})
    bad = datasets.check_samplesheet("sample,reads\nA,x.fastq.gz\n", {"x.fastq.gz"})
    other = datasets.check_samplesheet("sample,fastq_1\nA,y.fastq.gz\n", {"x.fastq.gz"})
    assert good == {"ok": True} and bad["ok"] is False and "fastq_1" in bad["message"] and other["ok"] is False
    monkeypatch.undo()
    assert len(up.datasets()) == before


def test_tc124_to_tc126_nothing_of_the_later_work_is_there(up):
    # TC-124, TC-125, TC-126
    up.register_dataset()
    c = up.client()
    batch = up.ok(c, version="v9")
    for url in ("/upload", "/upload?lang=en", "/upload/" + batch):
        text = c.get(url).text
        assert "<script" not in text.lower() and "drop" not in text.lower() and "dragover" not in text.lower()
        assert "schema" not in text.lower() and "checksum" not in text.lower()
        assert not re.search(r"<th>(版本|Version)</th>", text) and "已上傳資料" not in text and "Uploaded data" not in text
    assert len(re.findall(r'type="file"', c.get("/upload").text)) == 2


def test_tc127_a_slurm_environment_cannot_take_a_web_upload(up):
    # TC-127
    up.slurm_for_alice()
    r = up.post(ce="nchc1")
    assert 400 <= r.status_code < 500 and up.jobs() == [] and only_files(up) == [] and nothing_left(up)


def test_tc128_the_routes_with_upload_in_them(up):
    # TC-128
    routes = sorted((r.path, tuple(sorted(r.methods))) for r in up.client().app.routes if "upload" in r.path)
    assert routes == [("/upload", ("GET", "HEAD")), ("/upload", ("POST",)), ("/upload/{batch}", ("GET", "HEAD"))]


def test_tc129_no_tool_uploads_a_file(up):
    # TC-129
    tools, _ = up.w.mcp([])
    assert not [t.name for t in tools if "upload" in t.name.lower() or t.name.lower().startswith("put")]
    import asyncio
    from abf_platform.actions import chat_tools
    specs = asyncio.run(chat_tools.tool_specs(str(up.w.ip.index), None))
    assert specs and not [s["name"] for s in specs if "upload" in s["name"].lower()]


def test_tc133_no_secret_is_in_a_page_a_record_or_the_log(up, caplog):
    # TC-133: the session cookie and the password never appear; the form token only as a hidden field of the form
    import logging
    caplog.set_level(logging.DEBUG)
    c = up.client()
    cookie = c.cookies.get("abf_web")
    token = up.token(c)
    ok_batch = up.ok(c)
    pages = [c.get("/upload"), c.get("/upload/" + ok_batch)]
    finish_all(up)
    pages.append(c.get("/upload/" + ok_batch))
    pages.append(up.post(c, files=((R1, b""),)))
    pages.append(up.post(c, name="", version="v2"))
    from human_harness import PASSWORD
    for r in pages:
        assert cookie not in r.text and PASSWORD not in r.text and cookie not in str(r.headers) and token not in r.headers.get("location", "")
        for m in re.finditer(re.escape(token), r.text):
            assert r.text[max(0, m.start() - 40):m.start()].endswith('name="csrf" value="')
    record = json.dumps(up.record(ok_batch))
    assert cookie not in record and token not in record and PASSWORD not in record
    assert cookie not in caplog.text and token not in caplog.text and PASSWORD not in caplog.text


def test_tc134_the_platform_opens_no_outside_connection(up, monkeypatch):
    # TC-134
    import socket
    seen = []

    def refuse(self, *a, **k):
        seen.append(a)
        raise AssertionError("a connection was opened")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    c = up.client()
    batch = up.ok(c)
    finish_all(up)
    assert "已登記" in c.get("/upload/" + batch).text and seen == []


def test_tc135_the_new_files_import_no_network_or_cloud_client():
    # TC-135
    banned = {"socket", "urllib", "http", "requests", "boto3", "botocore", "httpx", "google", "ssl", "subprocess", "aiohttp"}
    for name in ("web_upload.py", "uploads_web.py", "actions/uploads.py"):
        tree = ast.parse(source(name))
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                found.add((node.module or "").split(".")[0])
        assert not found & banned, (name, found & banned)
    web = source("web.py")
    assert "default-src 'none'; style-src %s; form-action 'self'; frame-ancestors 'none'; base-uri 'none'" in web


# --- END ---


def test_tc101_design_md_upload_data_paragraph():
    # TC-101
    text = (PLATFORM_DIR.parent / "DESIGN.md").read_text(encoding="utf-8")
    assert "10-28 第一刀：表單上傳＋進度頁；拖放、依 schema 建表、已上傳資料表格留待後續" in text
    assert "platform keeps no copy" not in text
    assert "the platform host holds one staged copy until the size in the bucket matches, then it is deleted" in text
