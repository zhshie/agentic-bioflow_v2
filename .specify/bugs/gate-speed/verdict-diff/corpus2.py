#!/usr/bin/env python3
# Acceptance-round additions to the verdict-diff corpus: multi-document and NUL
# inputs, and large inputs (40 / 130 / 300 KB). Usage: corpus2.py <corpus dir>
import json, os, sys
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

def e(tool, ti, **kw):
    d = {"session_id": "s1", "cwd": "@CWD@", "transcript_path": "@TP@", "hook_event_name": "PreToolUse",
         "tool_name": tool, "tool_input": ti}
    d.update(kw)
    return json.dumps(d)

def put(name, data, binary=False):
    with open(os.path.join(OUT, name), "wb") as f:
        f.write(data if binary else data.encode("utf-8"))

# --- multi-document inputs, one of them dropped by a filter that skips non-strings
ls = e("Bash", {"command": "ls"})
multi = {
 "md1_tooln_rm": ls + e(5, {"command": "rm -rf results"}),
 "md1b_tooln_rm_nl": ls + "\n" + e(5, {"command": "rm -rf /work/u/lab_runs/x/results"}),
 "md2_sep_rm": ls + e("Bash", {"command": "rm -rf results\u001f"}),
 "md2b_sep_rm_notool": ls + json.dumps({"tool_input": {"command": "rm -rf results\u001f"}}),
 "md3_obj_launch": ls + e({"a": 1}, {"command": "tw launch x"}),
 "md3b_sep_launch_notool": ls + json.dumps({"tool_input": {"command": "tw launch x\u001f"}}),
 "md4_first_dropped_launch": e("Bash", {"command": "tw launch x\u001f"}) + ls,
 "md4b_first_dropped_rm": e("Bash", {"command": "rm -rf results\u001f"}) + ls,
 "md5_tp_obj_launch": ls + e("Bash", {"command": "tw launch x"}, transcript_path={"a": 1}),
 "md6_guard_root": e("Write", {"file_path": "/tmp/a.txt", "content": "x"}) + e("Write", {"file_path": "@ROOT@/hooks/x.sh", "command": {}}),
 "md6b_guard_root_bash": ls + json.dumps({"tool_name": "Bash", "tool_input": {"command": "rm @ROOT@/hooks/x.sh\u001f"}}),
 "md7_write_analysis": e("Write", {"file_path": "/tmp/a.txt", "content": "x"}) + e("Write", {"file_path": "/x/analysis/a.R", "content": {"a": 1}}),
 "md8_two_good_rm_first": e("Bash", {"command": "rm -rf results"}) + ls,
 "md8b_two_good_launch_second": ls + e("Bash", {"command": "tw launch x"}),
 "md9_trailing_garbage": ls + " garbage",
}
for k, v in multi.items():
    put(k + ".json", v)

# --- NUL bytes
base = e("Bash", {"command": "rm -rf results"})
put("nul_in_value.json", base.replace("rm -rf", "rm -\x00rf"), False)
put("nul_before.json", "\x00" + base)
put("nul_mid_key.json", base.replace("tool_name", "tool_\x00name"))
put("nul_after.json", base + "\x00")
put("nul_launch.json", e("Bash", {"command": "tw launch x"}).replace("tw launch", "tw\x00 launch"))
put("nul_json_escape.json", e("Bash", {"command": "rm -rf results\u0000"}))

# --- large inputs
def pad(kb):
    return "".join("x%d = %d  # filler line\n" % (i, i) for i in range(200000))[: kb * 1024]
for kb in (40, 130, 300):
    p = pad(kb)
    put("big%d_write_analysis.json" % kb, e("Write", {"file_path": "@CWD@/analysis/de.R", "content": p}))
    put("big%d_write_sheet.json" % kb, e("Write", {"file_path": "@CWD@/samplesheet.csv", "content": "sample,fastq_1\n" + p}))
    put("big%d_write_plain.json" % kb, e("Write", {"file_path": "/tmp/big.txt", "content": p}))
    put("big%d_write_plugin.json" % kb, e("Write", {"file_path": "@ROOT@/hooks/big.sh", "content": p}))
    put("big%d_heredoc_rm.json" % kb, e("Bash", {"command": "python3 - <<'EOF'\n" + p + "EOF\nrm -rf /work/u/lab_runs/x/results"}))
    put("big%d_heredoc_launch.json" % kb, e("Bash", {"command": "python3 - <<'EOF'\n" + p + "EOF\ntw launch nf-core/rnaseq -profile test"}))
    put("big%d_heredoc_ssh.json" % kb, e("Bash", {"command": "cat > notes.txt <<'EOF'\n" + p + "EOF\nssh host ls"}))
    put("big%d_cat_heredoc_plain.json" % kb, e("Bash", {"command": "cat > notes.txt <<'EOF'\n" + p + "EOF\nls"}))
    if kb < 300:  # a 300 KB single line outlasts a 60 s limit in the baseline too (awk, character by character)
        put("big%d_long_line.json" % kb, e("Bash", {"command": "echo " + "a" * (kb * 1024)}))
    put("big%d_many_newlines.json" % kb, e("Bash", {"command": "ls" + "\n" * (kb * 100)}))
    put("big%d_trailing_newlines.json" % kb, e("Bash", {"command": "rm -rf results" + "\n" * (kb * 100)}))
print(len(os.listdir(OUT)))
