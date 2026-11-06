# Nothing existing: pins the new cost wording in three documents (cost-docs-rewrite); no other test reads these strings.
"""cost-docs-rewrite: the cost spec in DESIGN.md, docs/CLOUD.md and docs/PLATFORM.md.
Test cases TC-001 ... TC-073 are named in the comments, see specs/cost-docs-rewrite/test-case.md.
Reads the three documents only: no network, nothing is started."""
import re

from helpers import REPO_ROOT

NOTE = "規格已定；程式尚未改（見 cost-reminder-quota 計畫）。在那之前，終端機指令仍是唯一寫入口，未設額度仍擋雲端送出。"
UNSET = "未設定每月費用提醒額度。實際費用以雲端帳單為準。"
NAME = "每月費用提醒額度"
TRANSITION = "（過渡：程式尚未改時）"


def _read(rel):
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _line(text, start):
    return next(ln for ln in text.splitlines() if ln.startswith(start))


def _section(text, head, nxt):
    i = text.index(head)
    j = text.index(nxt, i + len(head))
    return text[i:j]


def test_design_cost_item_is_per_environment_rows():
    # TC-001 TC-002 TC-003 TC-004 TC-005 TC-006 TC-008 TC-012
    cost = _line(_read("DESIGN.md"), "11. **Cost**")
    for need in ("per compute environment", "one row per compute environment", "expand", "never summed",
                 "not a bill", "Metrics", "environment / usage / status / scope", "Action-needed"):
        assert need in cost, need
    for bad in ("Reconciled", "NT$", "NCHC SU / Cloud used", "Estimate, bill pending", "cards", "cloud cap"):
        assert bad not in cost, bad


def test_design_settings_access_token_is_its_own_item():
    # TC-009 TC-011
    s = _line(_read("DESIGN.md"), "12. **Settings**")
    assert "Access token" in s
    assert "Personal" not in s
    assert "monthly cost reminder quota" in s


def test_cloud_doc_quota_is_user_set_and_unset_does_not_block():
    c = _read("docs/CLOUD.md")
    # TC-015
    assert c.splitlines()[0] == "# 雲端費用：預估、已用、每月費用提醒額度"
    # TC-017 TC-031
    for bad in ("只有管理者", "請找管理者調整上限", "請管理者替第一位使用者", "管理者替你設", "每人每月上限"):
        assert bad not in c, bad
    # TC-018 TC-019 TC-014 TC-020 TC-023
    assert "## 每月費用提醒額度（你自己設）" in c
    assert NAME in c and UNSET in c
    assert "請到網頁調整每月費用提醒額度，或下個月再送出" in c
    assert "只有三種寫法" not in c and "四種" in c
    assert "請本人把額度設小一點，例如 5 美元" in c
    # TC-018 (e): range on one line
    assert any("1,000,000" in ln and "0" in ln for ln in c.splitlines())
    # TC-026 TC-027 TC-013: the status note in three places
    assert c.count(NOTE) >= 3
    sec = _section(c, "## 拒絕的時候看到什麼", "## 目前的限制")
    assert NOTE in sec and "現行程式仍顯示舊訊息，將由 cost-reminder-quota 計畫改" in sec
    # TC-028 TC-016: the transition paragraph holds the old sentences
    trans = c[c.index(TRANSITION):]
    for need in ("abf-platform user add <名字> --lab <實驗室> --cloud-cap-usd 20", "abf-platform user cloud-cap <名字> 25",
                 "這是平台主機上的舊寫入口，將由使用者網頁取代", NOTE):
        assert need in trans, need
    body = c[:c.index(TRANSITION)]
    for old in ("沒有任何網頁、MCP 工具或聊天指令能讀或改它", "沒設上限就不能送到雲端（安全預設）", "管理者把上限調低"):
        assert old not in body and old in trans, old


def test_cloud_doc_teaches_cloud_budget_and_never_reads_it():
    c = _read("docs/CLOUD.md")
    head = "## 雲端預算：帳戶擁有者自己設（abf 只教）"
    assert head in c
    sec = c[c.index(head):]
    nxt = re.search(r"\n## ", sec[len(head):])
    sec = sec[:len(head) + nxt.start()] if nxt else sec
    for need in ("帳戶擁有者", "abf 只教", "不讀雲端預算", "Cost allocation tags", "Budgets", "Billing and Cost Management",
                 "Budgets & alerts", "Cost Management", "tag inheritance"):
        assert need in sec, need
    # TC-039: no links in this section; TC-040: no Taiwan dollars
    assert "http://" not in sec and "https://" not in sec
    for bad in ("NT$", "新台幣", "匯率"):
        assert bad not in sec
    # TC-034: the permission only in a "not needed" sentence
    for ln in c.splitlines():
        if "budgets:ViewBudget" in ln:
            assert "不需要" in ln or "不要" in ln, ln


def test_platform_cloud_cap_lines_are_user_set():
    p = _read("docs/PLATFORM.md")
    for bad in ("The page cannot change it", "the administrator set", "set only by the administrator", "每人每月上限"):
        assert bad not in p, bad
    assert NAME in p and NOTE in p
    row = next(ln for ln in p.splitlines() if "`tokens.db` (`cloud_caps`)" in ln)
    assert "將由使用者網頁取代" in row


def test_aws_azure_sections_have_labels_and_pending_measurement():
    p = _read("docs/PLATFORM.md")
    aws = _section(p, "### AWS Batch", "### Azure Batch")
    azure = _section(p, "### Azure Batch", "### Kubernetes")
    for sec in (aws, azure):
        assert "abf-user=" in sec and "待實測" in sec and "帳單" in sec
    assert "abf-run=" in aws
    assert "abf-run=" not in azure
    assert "process.resourceLabels" in aws
