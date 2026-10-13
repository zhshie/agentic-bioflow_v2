# Nothing existing: end-to-end tests of the 007b follow-up (a refused launch is shown as refused, and its name can be used again); same real chain as test_launch_e2e.py.
"""Follow-up 1 of feature 007b through the real platform, the real agent and a fake site (TC-F2-01, TC-F2-12, TC-F1-01)."""
import shutil

import pytest

from launch_harness import QUESTION_LAUNCH
from test_launch_e2e import World

REFUSED = "已存在"


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    w = World(tmp_path_factory.mktemp("fu-e2e"))
    yield w
    w.close()


def sbatches(site):
    return [c for c in site.calls() if c.startswith("sbatch ") and "--version" not in c]


def test_tcf2_12_tcf2_01_tcf1_01_a_refused_name_is_used_again_and_the_refused_row_stays(world):
    # TC-F2-12: the folder of the name exists on the site, so the agent refuses and sbatch is never called
    site = world.site
    folder = site.work / "runs" / "run-reuse"
    folder.mkdir(parents=True)
    (folder / "keep.txt").write_text("mine")
    n_sbatch = len(sbatches(site))
    rc, screen = world.run_cli(*world.args("run-reuse"), answer="y\n")
    assert rc != 0 and REFUSED in screen, screen[-500:]
    assert len(sbatches(site)) == n_sbatch
    assert [p.name for p in folder.iterdir()] == ["keep.txt"] and (folder / "keep.txt").read_text() == "mine"
    old = world.rows("SELECT id, run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at, cancel_requested_at "
                     "FROM launches WHERE run_name = 'run-reuse'")
    assert len(old) == 1 and old[0][2] is None and old[0][7] is None
    refused_job = world.rows("SELECT id, state FROM jobs WHERE kind = 'launch_nextflow' ORDER BY id DESC")[0]
    assert refused_job[1] == "refused"
    # TC-F1-01: the listing says who refused and why, in the agent's words
    rc, listing = world.run_cli("launches")
    assert rc == 0 and "被代理拒絕：" in listing and REFUSED in listing and "結果不明" not in listing, listing
    # TC-F2-01: the name is free again (nothing was done on the site); the refused row is kept as it was
    shutil.rmtree(folder)
    site.set("sbatch_id", "2231948")
    total = len(world.rows("SELECT id FROM launches"))
    rc, screen = world.run_cli(*world.args("run-reuse"), answer="y\n")
    assert rc == 0 and "已送出：Slurm 工作編號 2231948" in screen, screen[-500:]
    rows = world.rows("SELECT id, run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at, cancel_requested_at "
                      "FROM launches WHERE run_name = 'run-reuse' ORDER BY id")
    assert len(rows) == 2 and rows[0] == old[0] and rows[1][2] == 2231948
    assert len(world.rows("SELECT id FROM launches")) == total + 1
    assert world.rows("SELECT state FROM jobs WHERE id = ?", (refused_job[0],))[0][0] == "refused"
