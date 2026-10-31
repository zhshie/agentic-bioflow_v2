# Nothing existing: searched Nextflow's own handling of http(s) input cells (it downloads them itself) and this repo's _param_path SCHEME rule (116b); the Slurm samplesheet check is this platform's own rule, so these tests drive it.
"""Slurm launches accept http(s) addresses as samplesheet cells (spec specs/slurm-url-cells/plan.md, "Failing-first tests" 1-7).

In process: no network, no program is started. Cloud launches keep refusing the same cells (test 7)."""
import asyncio
import copy
import json
import re

import pytest

from owner_harness import Duo, sql_rows
from human_harness import World
from test_dataset_launch import bundle_of
from test_gcb_ce import ip  # noqa: F401
from test_gcb_launch import SHEET as GCB_SHEET, box  # noqa: F401
from test_launch_bundle import render, refused

U1 = "https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/SRR6357070_1.fastq.gz"
U2 = "https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/SRR6357070_2.fastq.gz"
HEAD = ["sample", "fastq_1", "fastq_2", "strandedness"]
OUTSIDE = "/etc/outside/x.fastq.gz"
AWSKEY = "AKIA" + "ABCDEFGHIJKLMNOP"


def sheet(*rows):
    return [list(HEAD)] + [list(r) for r in rows]


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def test_1_https_cells_reach_the_bundle_byte_for_byte():
    # TC-1
    b = render(samplesheet=sheet(["s1", U1, U2, "auto"], ["s2", U1, U2, "auto"]))
    assert b["files"]["samplesheet.csv"] == "sample,fastq_1,fastq_2,strandedness\ns1,%s,%s,auto\ns2,%s,%s,auto\n" % (U1, U2, U1, U2)
    assert b["samplesheet"][1][1] == U1


def test_2_request_launch_with_https_cells_reaches_the_confirm_step(d):
    # TC-2
    text = "\n".join(",".join(r) for r in sheet(["s1", U1, U2, "auto"])) + "\n"
    out = asyncio.run(_actions().request_launch(d.state, pipeline="nf-core/rnaseq", revision="3.14.0", run_name="run-u",
                                                ce_name="lab-a", params={"genome": "GRCh38"}, caller=d.a, samplesheet_text=text))
    assert out.get("sent") is not False and out["state"] == "pending", out
    assert U1 in json.dumps(bundle_of(d, out)["files"]["samplesheet.csv"])


def _actions():
    from abf_platform import actions
    return actions


def test_3_http_is_accepted_other_schemes_are_refused():
    # TC-3
    render(samplesheet=sheet(["s1", "http://example.org/a_1.fq.gz", "http://example.org/a_2.fq.gz", "auto"]))
    render(samplesheet=sheet(["s1", "HTTPS://Example.org/a.fq.gz", "", "auto"]))
    for cell in ("file:///etc/passwd", "s3://b/x", "ftp://h/x", "https:///nohost", "https://", "gs://b/x", "az://c/x"):
        refused(samplesheet=sheet(["s1", cell, "", "auto"]))


def test_3b_refusal_sentences_of_other_schemes_are_unchanged_from_v3():
    # TC-3
    from abf_station import launch, rules
    for cell in ("file:///etc/passwd", "s3://b/x", "ftp://h/x"):
        with pytest.raises(launch.BundleError) as e:
            render(samplesheet=sheet(["s1", cell, "", "auto"]))
        assert rules.path_reason("路徑", rules.path_problem(cell)) in str(e.value)


def test_4_a_local_cell_outside_the_roots_is_still_refused_with_todays_sentence():
    # TC-4
    refused(r"samplesheet 第 3 列第 2 欄（fastq_1）: 路徑在允許讀取的範圍之外 \(outside the allowed read roots\)",
            samplesheet=sheet(["s1", U1, U2, "auto"], ["s2", OUTSIDE, "", "auto"]))


def test_5_a_credential_in_a_url_is_refused_and_never_echoed():
    # TC-5
    from abf_station import launch
    cell = "https://h/x?" + AWSKEY
    with pytest.raises(launch.BundleError) as e:
        render(samplesheet=sheet(["s1", cell, "", "auto"]))
    assert AWSKEY not in str(e.value)


def test_6_a_mixed_sheet_is_accepted():
    # TC-6
    b = render(samplesheet=sheet(["s1", U1, "/data/storage/rawdata/s1_2.fq.gz", "auto"]))
    assert "/data/storage/rawdata/s1_2.fq.gz" in b["files"]["samplesheet.csv"] and U1 in b["files"]["samplesheet.csv"]


def test_7_google_batch_and_aws_still_refuse_an_https_cell(box):
    # TC-7
    from abf_station import launch
    sh = [["sample", "fastq_1", "strandedness"], ["s1", "https://lab-bucket/x.fastq.gz", "auto"]]
    with pytest.raises(launch.BundleError):
        box.bundle(samplesheet=sh)
    from test_aws_launch import ace, SHEET as AWS_SHEET
    from test_gcb_launch import gce
    with pytest.raises(launch.BundleError):
        launch.render_aws_bundle(ce=ace(), agent="a1", facts=box.facts(), roots=[], run_name="run-a", pipeline="nf-core/rnaseq",
                                 revision="3.14.0", samplesheet=[AWS_SHEET[0], [AWS_SHEET[1][0], "https://b/x.fq.gz", AWS_SHEET[1][2]]],
                                 params={})
