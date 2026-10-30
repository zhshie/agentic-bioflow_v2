# Nothing existing: tests of the read-only list of installed nf-core modules that the site agent adds to a preflight (specs/settings-pick-installed); the list and its limits are ours.
"""settings-pick-installed, the station half: S01 ... S15 of specs/settings-pick-installed/test-case.md plus X04 and X05 (nothing but reads).
The fake site runs the agent's one command in a real bash, with a fake `module` function in front, so the shape of the command is tested too."""
import subprocess
import types

import pytest

from abf_station import handlers, rules
from abf_station.site import SiteResult

ENV = {"platform": "slurm-platform", "workDir": "/data/work", "headQueue": "normal"}
GOOD_AVAIL = ["biology/nf-core-ampliseq/2.18.0", "biology/nf-core-rnaseq/3.14.0", "biology/Nextflow/26.10.0", "foo/nf-core-bad;rm/1"]
SHOWS = {"biology/nf-core-ampliseq/2.18.0": 'setenv("FOO","1")\nsetenv("NFCORE_AMPLISEQ_HOME","/site/ampliseq")\nsetenv("BAR","2")'}


class FakeSite:
    """Answers the checks of a healthy site; the inventory command is run in bash against a fake `module`."""

    def __init__(self, avail=None, shows=None, module="ok", connect=True, avail_rc=0, inventory_raises=False, inventory_result=None):
        self.avail, self.shows, self.module = list(GOOD_AVAIL if avail is None else avail), (SHOWS if shows is None else shows), module
        self.connect, self.avail_rc, self.raises, self.canned = connect, avail_rc, inventory_raises, inventory_result
        self.commands = []

    def call(self, args, input=None, timeout=None):
        self.commands.append(list(args))
        cmd = args[0] if args else ""
        if args == ["--check-reach"]:
            return SiteResult(0 if self.connect else 255, b"", "" if self.connect else "on_site: needs-human reason=no-master")
        if "abf_inv=" in cmd:
            if self.raises:
                raise RuntimeError("the site script broke")
            if self.canned is not None:
                return self.canned
            return self.run_inventory(cmd)
        if "work_dir=" in cmd:
            return SiteResult(0, b"work_dir=dir\nwork_dir_writable=yes\nhas_sbatch=yes\nhas_squeue=yes\nhas_sinfo=yes\n", "")
        if "java -version" in cmd:
            return SiteResult(0, b"", 'openjdk version "17.0.9" 2023-10-17')
        if "nextflow -version" in cmd:
            return SiteResult(0, b"", "nextflow version 24.10.0")
        if "sinfo" in cmd:
            return SiteResult(0, b"normal*\n", "")
        return SiteResult(0, b"", "")

    def run_inventory(self, cmd):
        if self.module == "missing":
            prelude = ""
        else:
            avail = "\n".join(self.avail)
            lines = ["module() {", '  if [ "$1" = "-t" ]; then']
            lines.append("    printf '%s\\n' " + _sh(avail) + " >&2; return " + str(self.avail_rc) + ";")
            lines.append('  elif [ "$1" = "show" ]; then')
            for name, text in self.shows.items():
                lines.append('    if [ "$2" = ' + _sh(name) + " ]; then printf '%s\\n' " + _sh(text) + "; return 0; fi;")
            lines.append("    printf '%s\\n' 'whatis(\"x\")'; return 0;")
            lines.append("  fi; }")
            prelude = "\n".join(lines) + "\n"
        p = subprocess.run(["bash", "-c", prelude + cmd], capture_output=True, timeout=60)
        return SiteResult(p.returncode, p.stdout, p.stderr.decode("utf-8", errors="replace"))


def _sh(text):
    return "'" + text.replace("'", "'\\''") + "'"


def ctx_of(site):
    return types.SimpleNamespace(site=site, settings_file="/nonexistent")


def run(site, env=None):
    return handlers.preflight(rules.clean_environment(dict(ENV, **(env or {}))), ctx_of(site), inventory=True)


def by_pipeline(items):
    return {i["pipeline"]: i for i in items}


def test_s01_two_nf_core_modules_only_and_five_fields():
    # S01
    inv = run(FakeSite())["site_inventory"]
    assert inv["status"] == "ok" and len(inv["items"]) == 2
    got = by_pipeline(inv["items"])
    assert set(got) == {"nf-core/ampliseq", "nf-core/rnaseq"}
    for item in inv["items"]:
        assert set(item) == {"pipeline", "revision", "module", "home", "home_source"}
    assert got["nf-core/ampliseq"]["revision"] == "2.18.0" and got["nf-core/ampliseq"]["module"] == "biology/nf-core-ampliseq/2.18.0"
    assert got["nf-core/rnaseq"]["revision"] == "3.14.0"
    assert not any("Nextflow" in i["module"] or "rm" in i["module"].split("/")[-2] for i in inv["items"])


def test_s02_a_variable_that_module_show_names():
    # S02
    item = by_pipeline(run(FakeSite())["site_inventory"]["items"])["nf-core/ampliseq"]
    assert item["home"] == "NFCORE_AMPLISEQ_HOME" and item["home_source"] == "module"


def test_s03_a_missing_variable_is_guessed_and_hyphens_become_underscores():
    # S03
    got = by_pipeline(run(FakeSite())["site_inventory"]["items"])["nf-core/rnaseq"]
    assert got["home"] == "NFCORE_RNASEQ_HOME" and got["home_source"] == "guessed"
    more = run(FakeSite(avail=["b/nf-core-sarek/3.4.0", "b/nf-core-scrna-seq/1.0.0"], shows={}))["site_inventory"]["items"]
    homes = {i["pipeline"]: i["home"] for i in more}
    assert homes == {"nf-core/sarek": "NFCORE_SAREK_HOME", "nf-core/scrna-seq": "NFCORE_SCRNA_SEQ_HOME"}


def test_s04_no_module_system():
    # S04
    inv = run(FakeSite(module="missing"))["site_inventory"]
    assert inv["status"] == "no_module_system" and inv["items"] == []
    canned = SiteResult(127, b"", "bash: module: command not found")
    inv = run(FakeSite(inventory_result=canned))["site_inventory"]
    assert inv["status"] == "no_module_system" and inv["items"] == []


@pytest.mark.parametrize("how", ["rc", "timeout", "raises", "garbage"])
def test_s05_a_failed_read_is_error(how):
    # S05
    site = {"rc": FakeSite(avail_rc=1), "timeout": FakeSite(inventory_result=SiteResult(124, b"", "", timed_out=True)),
            "raises": FakeSite(inventory_raises=True), "garbage": FakeSite(inventory_result=SiteResult(0, b"hello\n", ""))}[how]
    inv = run(site)["site_inventory"]
    assert inv["status"] == "error" and inv["items"] == [] and inv["reason"]


def test_s06_the_verdict_does_not_depend_on_the_inventory():
    # S06
    outs = [run(s) for s in (FakeSite(), FakeSite(module="missing"), FakeSite(avail_rc=1))]
    outs.append(handlers.preflight(rules.clean_environment(dict(ENV)), ctx_of(FakeSite())))
    first = outs[0]
    for out in outs:
        assert (out["ok"], out["checks"], out["message"]) == (first["ok"], first["checks"], first["message"])
        assert not any("inventory" in c["name"] for c in out["checks"])
    assert "site_inventory" not in outs[3] and all("site_inventory" in o for o in outs[:3])


@pytest.mark.parametrize("platform_module", ["gcb_preflight", "aws_preflight", "azure_preflight"])
def test_s07_a_cloud_environment_has_no_inventory(monkeypatch, platform_module):
    # S07
    mod = getattr(handlers, platform_module)
    monkeypatch.setattr(mod, "run_preflight", lambda env, cred_path=None: {"checks": [{"name": "x", "status": "pass", "detail": "ok"}]})
    monkeypatch.setattr(mod, "clean_environment", lambda ce: ce)
    site = FakeSite()
    state, result = handlers.handle({"kind": "preflight", "args": {"ce": {"platform": mod.TYPE}}}, ctx_of(site))
    assert state == "done" and "site_inventory" not in result
    assert not [c for c in site.commands if "module" in " ".join(c)]


def test_s08_the_command_holds_nothing_from_the_settings():
    # S08
    one = FakeSite()
    two = FakeSite()
    mark = lambda tag: {"modules": ["m/%s" % tag], "siteConfigVars": ["VAR_%s" % tag.upper()], "workDir": "/data/w%s" % tag,
                        "sitePipelines": [{"pipeline": "nf-core/%s" % tag, "revision": "1.0.0", "module": "m/%s" % tag, "home": "HOME_%s" % tag.upper()}]}
    run(one, mark("uniqueone"))
    run(two, mark("uniquetwo"))
    cmd = lambda site: [c[0] for c in site.commands if "abf_inv=" in c[0]]
    assert len(cmd(one)) == 1 and cmd(one) == cmd(two)
    for tag in ("uniqueone", "uniquetwo", "UNIQUEONE"):
        assert tag not in cmd(one)[0]


def test_s09_one_read_only_call():
    # S09 and X04
    site = FakeSite()
    run(site)
    mine = [c[0] for c in site.commands if "abf_inv=" in c[0]]
    assert len(mine) == 1 and "module -t avail" in mine[0] and "module show" in mine[0]
    for word in ("module load", "install", "rm ", " rm", ">/", "> /", "pip", "conda", "mkdir", "touch", "sbatch"):
        assert word not in mine[0].replace(">/dev/null", "").replace("2>&1", "")
    assert not [c for c in site.commands if "module avail" in c[0] or "find " in c[0] or "ls " in c[0]]      # X05: no other place is explored


def test_s10_a_bad_entry_is_dropped_not_the_whole_list():
    # S10
    avail = ["biology/nf-core-foo/main", "biology/nf-core-" + "a" * 70 + "/1.0", "biology/nf-core-ampliseq/2.18.0"]
    inv = run(FakeSite(avail=avail))["site_inventory"]
    assert inv["status"] == "ok" and [i["pipeline"] for i in inv["items"]] == ["nf-core/ampliseq"]


def test_s11_at_most_two_hundred():
    # S11
    avail = ["b/nf-core-p%d/1.0.0" % i for i in range(250)]
    inv = run(FakeSite(avail=avail, shows={}))["site_inventory"]
    assert inv["status"] == "ok" and 0 < len(inv["items"]) <= 200


def test_s12_no_connection_no_inventory():
    # S12
    site = FakeSite(connect=False)
    out = run(site)
    assert "site_inventory" not in out and out["ok"] is False and out["checks"][0]["name"] == "connect" and out["checks"][0]["status"] == "fail"
    assert not [c for c in site.commands if "module" in " ".join(c)]


def test_s13_read_at_is_always_there():
    # S13
    for site in (FakeSite(), FakeSite(module="missing"), FakeSite(avail_rc=1)):
        assert run(site)["site_inventory"]["read_at"]


def test_s14_a_long_list_is_read_to_the_end():
    # S14
    avail = ["x/other-%d/1.0" % i for i in range(300)] + ["biology/nf-core-ampliseq/2.18.0"]
    inv = run(FakeSite(avail=avail))["site_inventory"]
    assert [i["pipeline"] for i in inv["items"]] == ["nf-core/ampliseq"]


def test_s15_with_and_without_a_folder_prefix():
    # S15
    inv = run(FakeSite(avail=["nf-core-atacseq/2.1.2", "biology/nf-core-atacseq/2.1.2"], shows={}))["site_inventory"]
    assert len(inv["items"]) == 2
    assert {(i["pipeline"], i["revision"]) for i in inv["items"]} == {("nf-core/atacseq", "2.1.2")}
    assert {i["module"] for i in inv["items"]} == {"nf-core-atacseq/2.1.2", "biology/nf-core-atacseq/2.1.2"}


def test_the_preflight_job_reads_the_list_and_a_launch_does_not(monkeypatch):
    # the job the person asks for carries the list; the gate of a launch is the same checks without it
    site = FakeSite()
    state, result = handlers.handle({"kind": "preflight", "args": {"ce": dict(ENV)}}, ctx_of(site))
    assert state == "done" and result["site_inventory"]["status"] == "ok"
    seen = []
    from abf_station import launch
    monkeypatch.setattr(launch, "run_launch", lambda job, ctx, pre: seen.append(pre) or ("done", {}))
    handlers.handle({"kind": "launch_nextflow", "args": {}}, ctx_of(FakeSite()))
    quiet = FakeSite()
    assert "site_inventory" not in seen[0](rules.clean_environment(dict(ENV)), ctx_of(quiet))
    assert not [c for c in quiet.commands if "abf_inv=" in c[0]]
