# Nothing existing: nf-core and Seqera keep no per-person, versioned store of canvas graphs, and the owner rule for it (what is not yours answers like what does not exist) is this platform's own.
"""017b: composed pipelines are kept per owner, with append-only versions (`actions.pipelines`). Test cases are named in the
comments (TC-079 ...), see specs/017b-compose/test-case.md."""
import copy
import json
import logging
import re
import sqlite3
from pathlib import Path

import pytest

from human_harness import World
from owner_harness import Duo, sql_exec, sql_rows

HERE = Path(__file__).resolve().parent
PLATFORM = HERE.parent
FIXTURES = HERE / "fixtures" / "compose"
MODULE = PLATFORM / "abf_platform" / "actions" / "pipelines.py"
COMPOSE = PLATFORM / "abf_platform" / "compose.py"
SHA = "5ed90b42e78410e7411e9c6bdfeff33226d6c58e"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def pl():
    from abf_platform.actions import pipelines
    return pipelines


def qc_graph():
    return json.loads((FIXTURES / "fastqc_multiqc" / "graph.json").read_text(encoding="utf-8"))


def other_graph(n=1):
    return {"nodes": [{"id": "x%d" % i, "module": "fastqc"} for i in range(n)]}


def make(d, caller, name="demo-qc", graph=None, **kw):
    return pl().create_pipeline(d.state, name=name, graph=graph if graph is not None else qc_graph(), caller=caller, **kw)


def count(d, table):
    try:
        return sql_rows(d.state, "SELECT COUNT(*) AS n FROM %s" % table)[0]["n"]
    except sqlite3.OperationalError:
        return 0


def words(text, name):
    return re.sub(re.escape(str(name)), "<name>", str(text))


# ---- US3: create, version, read -----------------------------------------------------------------------------------------

def test_create_then_get_roundtrips_the_canonical_graph(d):
    # TC-079, TC-080, TC-081
    from abf_platform import compose
    r = make(d, d.a)
    assert r["ok"] is True and sorted(r["pipeline"]) == ["created_at", "id", "name", "version"]
    assert r["pipeline"]["name"] == "demo-qc" and r["pipeline"]["version"] == 1
    got = pl().get_pipeline(d.state, r["pipeline"]["id"], caller=d.a)
    canonical = compose.normalize(qc_graph())[0]
    assert got["ok"] and got["found"] and got["name"] == "demo-qc" and got["version"] == 1 and got["versions"] == [1]
    assert got["graph"] == canonical
    text = sql_rows(d.state, "SELECT graph_json FROM pipeline_versions")[0]["graph_json"]
    assert text == json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def test_update_appends_a_version_and_old_ones_do_not_change(d):
    # TC-082, TC-083, TC-084
    pid = make(d, d.a)["pipeline"]["id"]
    first = sql_rows(d.state, "SELECT graph_json FROM pipeline_versions WHERE version = 1")[0]["graph_json"]
    assert pl().update_pipeline(d.state, pid, graph=other_graph(1), caller=d.a)["pipeline"]["version"] == 2
    assert pl().update_pipeline(d.state, pid, graph=other_graph(2), caller=d.a)["pipeline"]["version"] == 3
    got = pl().get_pipeline(d.state, pid, caller=d.a)
    assert got["versions"] == [1, 2, 3] and got["version"] == 3 and len(got["graph"]["nodes"]) == 2
    assert sql_rows(d.state, "SELECT graph_json FROM pipeline_versions WHERE version = 1")[0]["graph_json"] == first
    old = pl().get_pipeline(d.state, pid, 1, caller=d.a)
    assert old["version"] == 1 and len(old["graph"]["nodes"]) == 2 and old["graph"]["nodes"][0]["id"] == "qc"


def test_update_with_the_same_graph_makes_no_new_version(d):
    # TC-085
    pid = make(d, d.a)["pipeline"]["id"]
    shuffled = qc_graph()
    shuffled["nodes"].reverse()
    r = pl().update_pipeline(d.state, pid, graph=shuffled, caller=d.a)
    assert r["ok"] is True and r["unchanged"] is True and r["pipeline"]["version"] == 1 and r["pipeline"]["id"] == pid
    assert count(d, "pipeline_versions") == 1


def test_list_is_own_only_with_the_fields_and_sorted(d):
    # TC-086, TC-087, TC-110
    make(d, d.a, name="zeta")
    two = make(d, d.a, name="alpha")["pipeline"]["id"]
    pl().update_pipeline(d.state, two, graph=other_graph(), caller=d.a)
    make(d, d.b, name="mine")
    rows = pl().list_pipelines(d.state, caller=d.a)["pipelines"]
    assert [r["name"] for r in rows] == ["alpha", "zeta"]
    assert sorted(rows[0]) == ["created_at", "id", "n_nodes", "name", "updated_at", "version"]
    assert rows[0]["version"] == 2 and rows[0]["n_nodes"] == 1 and rows[1]["n_nodes"] == 2
    assert [r["name"] for r in pl().list_pipelines(d.state, caller=d.b)["pipelines"]] == ["mine"]


def test_render_pipeline_gives_the_golden_files(d):
    # TC-088, TC-089, TC-090
    pid = make(d, d.a)["pipeline"]["id"]
    out = pl().render_pipeline(d.state, pid, caller=d.a)
    assert out["ok"] and out["name"] == "demo-qc" and out["version"] == 1 and "open_inputs" in out
    for f in ("main.nf", "modules.json", "nextflow.config"):
        assert out["files"][f] == (FIXTURES / "fastqc_multiqc" / f).read_text(encoding="utf-8")
    pl().update_pipeline(d.state, pid, graph=other_graph(), caller=d.a)
    assert "v1" in pl().render_pipeline(d.state, pid, 1, caller=d.a)["files"]["main.nf"]
    assert "v2" in pl().render_pipeline(d.state, pid, caller=d.a)["files"]["main.nf"]


def test_same_name_twice_is_refused_per_owner_but_other_owner_may_reuse_it(d):
    # TC-091, TC-100, TC-101
    assert make(d, d.a)["ok"] and make(d, d.b)["ok"]
    r = make(d, d.a)
    assert r["ok"] is False and r["message"] == ("你已經有一個叫 demo-qc 的組合；用 update 存新版本 "
                                                 "(a pipeline named demo-qc already exists; save a new version instead)")
    assert count(d, "pipelines") == 2
    assert make(d, None)["ok"] is True
    again = make(d, None)
    assert again["ok"] is False and again["message"] == r["message"] and count(d, "pipelines") == 3


def test_terminal_caller_none_sees_everything(d):
    # TC-092, TC-093
    a = make(d, d.a)["pipeline"]["id"]
    b = make(d, d.b, name="mine")["pipeline"]["id"]
    t = make(d, None, name="term")["pipeline"]["id"]
    assert sorted(r["name"] for r in pl().list_pipelines(d.state)["pipelines"]) == ["demo-qc", "mine", "term"]
    for pid in (a, b, t):
        assert pl().get_pipeline(d.state, pid)["found"] and pl().render_pipeline(d.state, pid)["ok"]
    assert "term" not in [r["name"] for r in pl().list_pipelines(d.state, caller=d.a)["pipelines"]]
    assert pl().get_pipeline(d.state, t, caller=d.a)["found"] is False


def test_old_platform_db_works_without_a_migration(d):
    # TC-094, TC-095, TC-096, TC-129
    from abf_platform import store
    assert "pipelines" not in store.STATE_SCHEMA
    tables = {r["name"] for r in sql_rows(d.state, "SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert not {"pipelines", "pipeline_versions"} & tables
    assert pl().list_pipelines(d.state, caller=d.a) == {"ok": True, "pipelines": []}
    sql_exec(d.state, "DROP TABLE pipeline_versions")
    sql_exec(d.state, "DROP TABLE pipelines")
    g = pl().get_pipeline(d.state, 7, caller=d.a)
    assert g["ok"] is False and g["found"] is False
    sql_exec(d.state, "DROP TABLE pipeline_versions")
    sql_exec(d.state, "DROP TABLE pipelines")
    assert make(d, d.a)["ok"] is True


def test_a_failure_while_writing_leaves_no_half_pipeline(d):
    # TC-097
    pl().list_pipelines(d.state, caller=d.a)                                   # the tables exist
    sql_exec(d.state, "CREATE TRIGGER boom BEFORE INSERT ON pipeline_versions BEGIN SELECT RAISE(ABORT, 'injected'); END")
    r = make(d, d.a)
    assert r["ok"] is False and "injected" not in json.dumps(r)
    assert count(d, "pipelines") == 0 and count(d, "pipeline_versions") == 0


# ---- exceptions ---------------------------------------------------------------------------------------------------------

def test_invalid_graph_writes_nothing(d):
    # TC-098, TC-102
    r = make(d, d.a, graph={"nodes": [{"id": "a", "module": "nonesuch"}]})
    assert r["ok"] is False and r["message"] == r["problems"][0] and "nonesuch" in r["message"]
    assert count(d, "pipelines") == 0 and count(d, "pipeline_versions") == 0
    pid = make(d, d.a)["pipeline"]["id"]
    bad = pl().update_pipeline(d.state, pid, graph={"nodes": [{"id": "a", "module": "nonesuch"}]}, caller=d.a)
    assert bad["ok"] is False and count(d, "pipeline_versions") == 1


def test_bad_names_are_refused(d):
    # TC-099
    for name in ("Demo", "1demo", "my_qc", "a" * 41, "", None):
        assert make(d, d.a, name=name)["ok"] is False
    assert count(d, "pipelines") == 0


def test_not_found_messages(d):
    # TC-103, TC-104, TC-105
    assert pl().update_pipeline(d.state, 999, graph=qc_graph(), caller=d.a)["message"] == "找不到這個組合 (pipeline not found): 999"
    pid = make(d, d.a)["pipeline"]["id"]
    r = pl().get_pipeline(d.state, pid, 5, caller=d.a)
    assert r["ok"] is False and r["found"] is False and r["message"]
    r = pl().get_pipeline(d.state, 999, caller=d.a)
    assert r["ok"] is False and r["found"] is False and r["message"]


def test_versions_table_refuses_update_and_delete(d):
    # TC-106, TC-107
    make(d, d.a)
    before = sql_rows(d.state, "SELECT * FROM pipeline_versions")[0]["graph_json"]
    for stmt in ("UPDATE pipeline_versions SET graph_json = '{}'", "DELETE FROM pipeline_versions"):
        with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)) as e:
            sql_exec(d.state, stmt)
        assert "pipeline versions are append-only" in str(e.value)
    assert sql_rows(d.state, "SELECT * FROM pipeline_versions")[0]["graph_json"] == before


def test_other_user_cannot_get_list_or_render(d):
    # TC-108, TC-109, TC-110, TC-111
    pid = make(d, d.a)["pipeline"]["id"]
    missing = 4242
    got, none = pl().get_pipeline(d.state, pid, caller=d.b), pl().get_pipeline(d.state, missing, caller=d.b)
    assert got["found"] is False and "graph" not in got
    assert words(got["message"], pid) == words(none["message"], missing)
    out = pl().render_pipeline(d.state, pid, caller=d.b)
    assert out["ok"] is False and "files" not in out
    assert words(out["message"], pid) == words(pl().render_pipeline(d.state, missing, caller=d.b)["message"], missing)
    assert pl().list_pipelines(d.state, caller=d.b)["pipelines"] == []
    assert d.a.name not in json.dumps(got)


def test_other_user_cannot_update(d):
    # TC-112, TC-113
    pid = make(d, d.a)["pipeline"]["id"]
    before = pl().get_pipeline(d.state, pid, caller=d.a)
    mine = pl().update_pipeline(d.state, pid, graph=other_graph(), caller=d.b)
    gone = pl().update_pipeline(d.state, 4242, graph=other_graph(), caller=d.b)
    assert mine["ok"] is False and words(mine["message"], pid) == words(gone["message"], 4242)
    assert mine["message"] == "找不到這個組合 (pipeline not found): %d" % pid
    assert pl().get_pipeline(d.state, pid, caller=d.a) == before and count(d, "pipeline_versions") == 1


def test_error_messages_hide_internals(d, caplog):
    # TC-114, TC-136
    caplog.set_level(logging.DEBUG)
    from abf_platform import store
    from human_harness import PASSWORD
    # TC-136: values the caller's account really holds; none of them may appear in any reply or log line.
    pat = store.create_token(d.w.ip.tokens, kind="pat", user_id=d.a.user_id, label="tc136")
    secrets_known = [pat, store.token_hash(pat), PASSWORD]
    for row in sql_rows(d.w.ip.tokens, "SELECT password_hash FROM users WHERE id = ?", (d.a.user_id,)):
        secrets_known.append(row["password_hash"])
    for row in sql_rows(d.w.ip.tokens, "SELECT token_hash FROM tokens"):
        secrets_known.append(row["token_hash"])
    assert all(secrets_known) and len(secrets_known) >= 4
    seen = []
    seen.append(make(d, d.a, graph={"nodes": [{"id": "a", "module": "nonesuch"}]}))
    pid = make(d, d.a)["pipeline"]["id"]
    seen.append(make(d, d.a))
    seen.append(pl().update_pipeline(d.state, 999, graph=qc_graph(), caller=d.a))
    seen.append(pl().get_pipeline(d.state, 999, caller=d.a))
    seen.append(pl().get_pipeline(d.state, pid, caller=d.b))
    seen.append(pl().render_pipeline(d.state, pid, caller=d.b))
    sql_exec(d.state, "CREATE TRIGGER boom BEFORE INSERT ON pipeline_versions BEGIN SELECT RAISE(ABORT, 'injected'); END")
    seen.append(make(d, d.a, name="other"))
    fine = [pl().list_pipelines(d.state, caller=d.a), pl().list_pipelines(d.state, caller=d.b),      # the five functions, answered too
            pl().get_pipeline(d.state, pid, caller=d.a), pl().render_pipeline(d.state, pid, caller=d.a)]
    text = json.dumps(seen + fine, ensure_ascii=False) + caplog.text
    for word in ("SELECT", "INSERT", "sqlite", "Traceback", "platform.db", str(d.state), "injected"):
        assert word not in text, word
    for known in secrets_known:
        assert known not in text, "a secret of the caller's account leaked"
    token_like = re.compile(r"abf_[a-z]+_[A-Za-z0-9]{8,}|scrypt|password", re.I)
    assert not token_like.search(text)
    for r in seen:
        assert re.search(r"[一-鿿]", r["message"]) and re.search(r"\([ -~]+\)", r["message"]), r["message"]


# ---- constitution -------------------------------------------------------------------------------------------------------

def test_no_confirmation_or_job_is_made(d):
    # TC-127
    tables = ["jobs", "confirmations", "launches"]

    def counts():
        return [sql_rows(d.state, "SELECT COUNT(*) AS n FROM %s" % t)[0]["n"] for t in tables]
    before = counts()
    pid = make(d, d.a)["pipeline"]["id"]
    pl().update_pipeline(d.state, pid, graph=other_graph(), caller=d.a)
    pl().render_pipeline(d.state, pid, caller=d.a)
    assert counts() == before


def test_pipelines_store_has_no_submit_path():
    # TC-126, TC-119
    for path in (MODULE, COMPOSE):
        s = path.read_text(encoding="utf-8")
        for word in ("subprocess", "os.system", "sbatch", "srun", "qsub", "confirm", "jobs", "queue",
                     "zipfile", "tarfile", "shutil", "urllib", "requests", "socket"):
            assert word not in s, (path.name, word)


def test_pipelines_columns_say_nothing_about_runs(d):
    # TC-128, TC-120
    make(d, d.a)
    cols = lambda t: sorted(c["name"] for c in sql_rows(d.state, "PRAGMA table_info(%s)" % t))
    assert cols("pipelines") == ["created_at", "id", "name", "owner_user_id"]
    assert cols("pipeline_versions") == ["created_at", "graph_json", "id", "pipeline_id", "version"]


def test_only_seven_public_functions_and_none_in_the_actions_package():
    # TC-117, TC-121
    import abf_platform.actions as actions
    m = pl()
    names = sorted(n for n, f in vars(m).items() if callable(f) and not n.startswith("_") and getattr(f, "__module__", "") == m.__name__)
    assert names == ["create_pipeline", "get_pipeline", "get_validation", "list_pipelines", "render_pipeline", "update_pipeline",
                     "validate_pipeline"]
    for n in names:
        assert not hasattr(actions, n), n


def test_the_files_owned_by_other_work_do_not_mention_pipelines():
    # TC-115, TC-116, TC-117 (lasting half; the diff against the base is the reviewer's)
    for f in ("actions/__init__.py", "mcp_server.py", "web.py", "store.py", "catalogue.py"):
        text = (PLATFORM / "abf_platform" / f).read_text(encoding="utf-8")
        for word in ("create_pipeline", "render_pipeline", "pipeline_versions", "actions.pipelines", "compose"):
            assert word not in text, (f, word)
