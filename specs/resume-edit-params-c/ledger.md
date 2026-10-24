# resume-edit-params-c ledger

- [x] A guidance FIXED_SENTENCE + test_tc107 line; B two skills; C ADR 0009 line, SEQERA_PARITY Resume row, CHANGELOG entry (second bullet: test_tc073 pins keep-submissions first); new test file.
- No migration needed. test_guidance tc404 (wheel copy) failed before this change too (checked on the stashed tree).

```
 CHANGELOG.md                                    |   1 +
 docs/SEQERA_PARITY.md                           |   2 +-
 docs/adr/0009-web-layout-three-panes.md         |   1 +
 platform/abf_platform/guidance.py               |   2 +-
 platform/tests/test_keep_submissions.py         |   2 +-
 platform/tests/test_resume_edit_params_words.py | 124 ++++++++++++++++++++++++
 skills/operational/SKILL.md                     |   2 +-
 skills/runs/SKILL.md                            |   6 +-
 8 files changed, 133 insertions(+), 7 deletions(-)

diff --git a/platform/abf_platform/guidance.py b/platform/abf_platform/guidance.py
index 8483134..064370f 100644
--- a/platform/abf_platform/guidance.py
+++ b/platform/abf_platform/guidance.py
@@ -16,7 +16,7 @@ MAX_BYTES = 2048
 FIXED_SENTENCE = ("Seven tools of this server are read-only. Each of the tools launch, cancel, resume and relaunch only asks: it "
                   "does not start anything until the person says yes in their own client's form or on the page that the answer "
                   "names, and you cannot say it for them (in the terminal, abf-platform launch, cancel, resume and relaunch ask "
-                  "the same way). A failed run is resumed or relaunched with its name alone. The tool forget only asks too: it "
+                  "the same way). A failed run is relaunched with its name alone; a resume may also carry changed parameters and extra resource settings. The tool forget only asks too: it "
                   "deletes nothing until the person says yes in their own client's form. The complete steps of each command "
                   "are the MCP prompt of the same name (setup, launch, runs, downstream, finish).")
 
diff --git a/platform/tests/test_keep_submissions.py b/platform/tests/test_keep_submissions.py
index 505cecf..7cb6dc5 100644
--- a/platform/tests/test_keep_submissions.py
+++ b/platform/tests/test_keep_submissions.py
@@ -847,7 +847,7 @@ def test_tc107_the_instructions_name_all_five_tools_and_keep_the_009e_sentence_w
     text = guidance.routing_instructions()
     for name in ("launch", "cancel", "resume", "relaunch", "forget"):
         assert name in text, name
-    assert "A failed run is resumed or relaunched with its name alone." in text
+    assert "A failed run is relaunched with its name alone; a resume may also carry changed parameters and extra resource settings." in text
     assert "deletes nothing until the person says yes" in guidance.FIXED_SENTENCE
     assert len(text.encode("utf-8")) <= guidance.MAX_BYTES
 
```
