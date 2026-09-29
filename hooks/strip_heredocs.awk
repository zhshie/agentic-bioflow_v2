# Remove here-document BODIES from a shell command, keeping every real line.
#
# Why this exists: launch_trigger.sh (sourced by confirm_launch.sh),
# confirm_cleanup.sh and confirm_walkthrough.sh each decide what a command
# does by splitting it into segments and testing each one. A here-doc body is
# made of lines, so its lines became segments - and a document that merely
# *mentions* a command was judged as if it ran it.
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
# A body fed to something that EXECUTES it is kept, because there the body is
# the command: `bash <<'EOF'`, `ssh host bash -s <<EOF`, `on_site.sh <<EOF`,
# `python3 - <<EOF`. Until #29 every body was dropped, on the reasoning that
# "this plugin never launches runs that way" - but the model is not bound by
# how this plugin launches, and `ssh host bash -s <<EOF ... rm -rf .../results`
# passed both gates with nothing printed. What counts as an executor is the
# command word of the segment that opens the here-doc (after `sudo`, `env`,
# VAR=value and a leading path); a writer like `cat > f` or `tee f` still has
# its body dropped, which is the case the stripping was written for.

# `<<<` is a here-STRING, not a here-doc. It is masked before scanning so
# `grep ... <<< "$VAR"` is not mistaken for a here-doc named "VAR".

# Does the text before `<<` hand the body to something that runs it?
function executes(pre,   seg, w) {
    seg = pre
    # the segment that opens the here-doc: text after the last separator
    while (match(seg, /(\|\||&&|[|;&(])/)) seg = substr(seg, RSTART + RLENGTH)
    sub(/^[ \t]+/, "", seg)
    while (1) {
        if (match(seg, /^(sudo|env|command|exec|nohup)[ \t]+/)) { seg = substr(seg, RLENGTH + 1); continue }
        if (match(seg, /^[A-Za-z_][A-Za-z0-9_]*=[^ \t]*[ \t]+/)) { seg = substr(seg, RLENGTH + 1); continue }
        if (match(seg, /^-[^ \t]*[ \t]+/)) { seg = substr(seg, RLENGTH + 1); continue }
        break
    }
    w = seg
    sub(/[ \t].*$/, "", w)
    sub(/^.*\//, "", w)
    return (w ~ /^(bash|sh|zsh|dash|ksh|ssh|on_site\.sh|python|python3|Rscript|R|perl|node|ruby)$/)
}

function scan(s,   m, d, isdash, pre, piped) {
    gsub(/<<</, "\001", s)
    pre = ""
    # `cat <<EOF | bash` hands the body to a shell through a pipe instead.
    piped = (s ~ /\|[ \t]*(sudo[ \t]+)?([^ \t|]*\/)?(bash|sh|zsh|dash|ksh|ssh)([ \t]|$)/)
    while (match(s, /<<-?[ \t]*("[^"]*"|'[^']*'|\\?[A-Za-z_][A-Za-z0-9_]*)/)) {
        m = substr(s, RSTART, RLENGTH)
        pre = pre substr(s, 1, RSTART - 1)
        s = substr(s, RSTART + RLENGTH)
        isdash = (m ~ /^<<-/)
        d = m
        sub(/^<<-?[ \t]*/, "", d)
        gsub(/["']/, "", d)
        sub(/^\\/, "", d)
        n++
        ddelim[n] = d
        ddash[n]  = isdash
        dkeep[n]  = piped || executes(pre)
    }
}

BEGIN { n = 0 }

{
    if (n > 0) {
        # Inside a body: drop this line unless an executor reads it. The terminator must be the whole line;
        # <<- lets it be indented with TABS (spaces do not count, per POSIX).
        t = $0
        if (ddash[1]) sub(/^\t+/, "", t)
        if (t == ddelim[1]) {
            for (i = 1; i < n; i++) { ddelim[i] = ddelim[i+1]; ddash[i] = ddash[i+1]; dkeep[i] = dkeep[i+1] }
            n--
            next
        }
        if (dkeep[1]) print
        next
    }
    scan($0)
    print
}
