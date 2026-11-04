#!/usr/bin/env python3
# Nothing existing: no library reads Nextflow's "cache hash" log lines and names the first entry that differs between two runs; this is a small read-only helper for the resume-cache-miss diagnosis.
"""Compare the task-hash dumps of two Nextflow runs and name the first field that differs.

    nf_hash_diff.py BEFORE.log AFTER.log

Both files are copies of `.nextflow.log` (made with `cp` on the login node), or the output of a run started with `-dump-hashes`. They are only
read. Standard library only: no network, no ssh, no sbatch, no nextflow.

Shape of the input (Nextflow's TaskProcessor, source nextflow.processor.TaskProcessor#createTaskHashKey; the 'cache hash' block is
written by the nextflow log at the point a task hash is computed; not yet compared with a real nano4 log, see the ledger):

    ... TaskProcessor - [FASTQC (s1)] cache hash: 5f8e...; mode: STANDARD; entries:
      d3f6...  [java.util.UUID] 7a2c...
      7c4d...  [java.lang.String] NFCORE_AMPLISEQ:AMPLISEQ:FASTQC
      9a10...  [java.lang.String] fastqc ...        (the script, may run over several lines)
      b27e...  [java.lang.String] quay.io/biocontainers/fastqc:0.12.1--hdfd78af_0
      c0ff...  [nextflow.util.ArrayBag] [FileHolder(sourceObj:/data/s1.fq, ...)]

Nextflow does not name the entries, so the name printed here is a guess from the entry's type and value: session, process, script,
container, input, other. Entries are compared in the order they appear. Exit status: 0 no difference, 1 a difference, 2 a file that cannot
be read or is not a hash log.
"""
import re
import sys

HEADER = re.compile(r"(?:^|\s-\s)\[(.+?)\] cache hash: ([0-9a-fA-F]+); mode: (\w+); entries:")
ENTRY = re.compile(r"^\s+([0-9a-fA-F]{8,})\s+\[([^\]\s]+)\]\s?(.*)$")
IMAGE = re.compile(r"^(?:(?:docker|oras|library|shub)://)?[\w.\-]+(?::\d+)?(?:/[\w.\-]+)+(?:[:@][\w.\-:]+)?$|^\S+\.(?:sif|img)$")


class NotAHashLog(Exception):
    pass


def parse(text):
    """{task name: [(hash, type, value), ...]} in file order; raises NotAHashLog when the text has no 'cache hash' block."""
    tasks, cur = {}, None
    for line in text.splitlines():
        h = HEADER.search(line)
        if h:
            cur = tasks.setdefault(h.group(1), [])
            continue
        if cur is None:
            continue
        e = ENTRY.match(line)
        if e:
            cur.append([e.group(1), e.group(2), e.group(3)])
        elif cur and line.strip() and not re.search(r"\b(INFO|DEBUG|TRACE|WARN|ERROR)\b", line[:60]):
            cur[-1][2] += "\n" + line           # the rest of a multi-line value, such as a script
    if not tasks:
        raise NotAHashLog()
    return {k: [tuple(x) for x in v] for k, v in tasks.items()}


def label(entries, i):
    """A name for entry i: session, process, script, container, input or other."""
    _, typ, val = entries[i]
    if typ.endswith("UUID"):
        return "session"
    if re.search(r"File|Path|ArrayBag|Bag", typ):
        return "input"
    if typ.endswith("String"):
        if "\n" in val or val.startswith("#!"):
            return "script"
        if IMAGE.match(val.strip()) and ("/" in val) and not val.startswith("/"):
            return "container"
        first_str = next((j for j in range(len(entries)) if entries[j][1].endswith("String")), None)
        if first_str == i:
            return "process"
    return "other"


def compare(a, b):
    """(None, "") when equal, else (field, message)."""
    for name, ea in a.items():
        eb = b.get(name)
        if eb is None:
            return "task", "只在第一份有的 task: %s（第二份沒有它；確認兩份是同一個 run 的前後兩次，且都包含這個 task）" % name
        for i in range(max(len(ea), len(eb))):
            if i >= len(ea) or i >= len(eb):
                side = "第二份" if i >= len(eb) else "第一份"
                got = ea if i >= len(ea) else eb
                return "missing", "task %s: %s少了第 %d 個欄位（%s）；兩份的欄位數不同，請確認兩份日誌都完整（沒有被截斷）" % (
                    name, side, i + 1, label(got, i) if i < len(got) else "?")
            if ea[i] != eb[i]:
                f = label(ea, i)
                if ea[i][2] == eb[i][2]:
                    why = "值相同但雜湊不同（檔案的大小或修改時間不同的典型樣子）"
                else:
                    why = "值不同"
                return f, "task %s: 第一個不同的欄位是 %s（第 %d 個）: %s\n  之前: [%s] %s\n  之後: [%s] %s" % (
                    name, f, i + 1, why, ea[i][1], ea[i][2][:200], eb[i][1], eb[i][2][:200])
    extra = [n for n in b if n not in a]
    if extra:
        return "task", "只在第二份有的 task: %s（第一份沒有它）" % extra[0]
    return None, ""


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError as e:
        raise NotAHashLog("讀不到 %s（%s）。請確認路徑，並先用 cp 把 .nextflow.log 複製到這裡。" % (path, e.strerror or "error"))


def main(argv):
    if len(argv) != 2:
        print("用法: nf_hash_diff.py 之前.log 之後.log", file=sys.stderr)
        return 2
    parsed = []
    for path in argv:
        try:
            parsed.append(parse(read(path)))
        except NotAHashLog as e:
            if e.args:
                print(e.args[0], file=sys.stderr)
                return 2
            print("格式不認得: %s 裡沒有 'cache hash: ...; entries:' 的區塊。請確認這是 .nextflow.log，且那次執行有記錄 task 雜湊"
                  "（見 docs/TESTING.md「續跑快取診斷」第二層 -dump-hashes）。" % argv[parsed.__len__()], file=sys.stderr)
            return 2
    field, msg = compare(*parsed)
    if field is None:
        print("無差異：兩份裡所有 task 的雜湊欄位都相同。")
        return 0
    print(msg)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
