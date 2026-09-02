# Remove here-document BODIES from a shell command, keeping every real line.
#
# Why this exists: confirm_nextflow.sh and confirm_cleanup.sh both decide what a
# command does by splitting it into segments and testing each one. A here-doc
# body is made of lines, so its lines became segments - and a document that
# merely *mentions* a command was judged as if it ran it.
#
#     cat > guide.md <<'EOF'
#     Submit with:
#       bash ${CLAUDE_PLUGIN_ROOT}/scripts/submit_run.sh <run_dir>
#     EOF
#
# The middle line is prose. The old code saw a segment matching submit_run.sh
# that was not on the read-only list, and armed the execution gate on a command
# that writes a text file. Same for the deletion guard and any path example.
#
# The introducing line is KEPT, deliberately: `cat > f <<EOF` really is a
# truncating redirect and the deletion guard must still see it.
#
# Only bodies are dropped, so a genuine `bash <<'EOF' ... EOF` that really does
# run commands is also hidden. That is accepted: this plugin never launches runs
# that way - it launches them through submit_run.sh on a normal command line.
#
# `<<<` is a here-STRING, not a here-doc. It is masked before scanning so
# `grep ... <<< "$VAR"` is not mistaken for a here-doc named "VAR".

function scan(s,   m, d, isdash) {
    gsub(/<<</, "\001", s)
    while (match(s, /<<-?[ \t]*("[^"]*"|'[^']*'|\\?[A-Za-z_][A-Za-z0-9_]*)/)) {
        m = substr(s, RSTART, RLENGTH)
        s = substr(s, RSTART + RLENGTH)
        isdash = (m ~ /^<<-/)
        d = m
        sub(/^<<-?[ \t]*/, "", d)
        gsub(/["']/, "", d)
        sub(/^\\/, "", d)
        n++
        ddelim[n] = d
        ddash[n]  = isdash
    }
}

BEGIN { n = 0 }

{
    if (n > 0) {
        # Inside a body: drop this line. The terminator must be the whole line;
        # <<- lets it be indented with TABS (spaces do not count, per POSIX).
        t = $0
        if (ddash[1]) sub(/^\t+/, "", t)
        if (t == ddelim[1]) {
            for (i = 1; i < n; i++) { ddelim[i] = ddelim[i+1]; ddash[i] = ddash[i+1] }
            n--
        }
        next
    }
    scan($0)
    print
}
