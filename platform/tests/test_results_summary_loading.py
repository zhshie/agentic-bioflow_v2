"""results-summary-loading: the two report cells under the summary cards say `Reading` while the first-level listing is being read.
Test cases are named in the comments (TC-001 ...)."""
import re

import pytest

from human_harness import World
from test_results_files import (RESULTS, card_cells, finish_listing, listings, mid, outputs_url, plain, seed, top_entries, world, NOW, HOUR)
from test_web_board import no_cjk


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def cell(cells, word):
    return re.search(r'<span class="off">%s .*?</span></span>' % re.escape(word), cells).group(0)


def test_loading_cells_say_reading(w):
    # TC-001, TC-002, TC-003, TC-004, TC-005, TC-009, TC-010, TC-011
    ann, c, rid = world(w)
    t = c.get(outputs_url(rid)).text
    cells = card_cells(t)
    for word in ("報告", "MultiQC 報告"):
        one = cell(cells, word)
        assert one == '<span class="off">%s <span class="ostat state-running">⟳ 讀取中</span></span>' % word
        assert "之後開放" not in one and "此管線沒有產生" not in one and "/run/file" not in one
    for word in ("指標", "全部下載"):
        assert '<span class="off">%s <span class="later">之後開放</span></span>' % word in cells
    assert "style=" not in t


def test_loading_cells_english(w):
    # TC-006, TC-007, TC-008
    ann, c, rid = world(w)
    t = c.get(outputs_url(rid, lang="en")).text
    cells = card_cells(t)
    for word in ("Report", "MultiQC report"):
        one = cell(cells, word)
        assert "Reading" in one and "Coming later" not in one
    for word in ("Metrics", "Download all"):
        assert '<span class="off">%s <span class="later">Coming later</span></span>' % word in cells
    assert no_cjk(mid(t))


def test_failed_listing_keeps_later_words(w):
    # TC-014, TC-015, TC-016
    ann, c, rid = world(w)
    c.get(outputs_url(rid))
    finish_listing(w, RESULTS, None, ok=False, error="not_found", message="no")
    cells = card_cells(c.get(outputs_url(rid)).text)
    for word in ("報告", "MultiQC 報告"):
        assert cell(cells, word) == '<span class="off">%s <span class="later">之後開放</span></span>' % word
    assert "讀取中" not in cells and "此管線沒有產生" not in cells and "/run/file" not in cells


def test_other_tabs_do_not_claim_reading(w):
    # TC-017, TC-018
    ann, c, rid = world(w)
    cells = card_cells(c.get(outputs_url(rid).replace("tab=outputs", "tab=tasks")).text)
    assert "讀取中" not in cells and cells.count("之後開放") == 4
    assert listings(w) == []


def test_other_tab_after_outputs_still_later(w):
    # TC-029
    ann, c, rid = world(w)
    c.get(outputs_url(rid))
    assert len(listings(w)) == 1
    cells = card_cells(c.get(outputs_url(rid).replace("tab=outputs", "tab=tasks")).text)
    assert "讀取中" not in cells and cells.count("之後開放") == 4


def test_subfolder_page_does_not_claim_reading(w):
    # TC-019
    ann, c, rid = world(w)
    cells = card_cells(c.get(outputs_url(rid, "multiqc")).text)
    assert "讀取中" not in cells and cells.count("之後開放") == 4


def test_no_record_run_does_not_claim_reading(w):
    # TC-020
    ann, c, rid = world(w, folder="")
    t = c.get(outputs_url(rid)).text
    cells = card_cells(t)
    assert "讀取中" not in cells and cells.count("之後開放") == 4


def test_ready_listing_still_gives_links_or_none(w):
    # TC-021, TC-022
    ann, c, rid = world(w)
    c.get(outputs_url(rid))
    finish_listing(w, RESULTS, top_entries())
    cells = card_cells(c.get(outputs_url(rid)).text)
    assert "讀取中" not in cells and cells.count("/run/file") == 2
    finish_listing(w, RESULTS, [])
    cells = card_cells(c.get(outputs_url(rid)).text)
    assert "讀取中" not in cells and "/run/file" not in cells and cells.count("此管線沒有產生") == 2
