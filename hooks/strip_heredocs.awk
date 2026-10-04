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

# #35: does a pipe in str hand its input to something that runs it? After the
# pipe come any wrappers (sudo -u x, srun --pty, env, timeout 60 ...) with their
# options, then a shell or an interpreter. The plain `| bash` is one case of it.
# hooks/strip_heredocs.awk carries the same two functions; keep them in step
# (tests/confirm_cleanup_test.sh and confirm_launch_test.sh pin both).
function is_runner(w) {
    sub(/^\\/, "", w); sub(/^.*\//, "", w); sub(/\.exe$/, "", w)
    return (w ~ /^(bash|sh|zsh|dash|ksh|pwsh|powershell|ssh|python[0-9.]*|perl|ruby|node|Rscript|R)$/)
}
# After independent acceptance (#35): does the runner at W[i] read its STDIN as code?
# A shell does, always. An interpreter does unless it was given a script file
# (`python3 count_words.py`): then stdin is data. ssh does unless it was given
# a remote command (`ssh t3 'cat >> notes.md'`), and a remote command that is
# itself a shell or an interpreter is judged the same way, one level down.
# A lone `-`, or -c/-e, keeps it code: `python3 -`, `python3 -u -`, `perl -ne`.
function reads_code(W, i, k, depth,   w, j, v, host, rw) {
    w = W[i]; sub(/^\\/, "", w); sub(/^.*\//, "", w); sub(/\.exe$/, "", w)
    if (w ~ /^(bash|sh|zsh|dash|ksh|pwsh|powershell)$/) return 1
    if (w == "ssh") {
        host = 0
        for (j = i + 1; j <= k; j++) {
            v = W[j]
            if (v == "") continue
            if (v ~ /^[0-9]*[<>]/ || v ~ /^&>/ || v ~ /^<</) continue
            if (!host) {
                if (v ~ /^-[bcDEeFIiJLlmOopQRSWw]$/) { j++; continue }
                if (v ~ /^-/) continue
                host = 1; continue
            }
            # the first word of the remote command
            rw = v; gsub(/^["']+/, "", rw)
            if (depth < 3) {
                W[j] = rw
                return reads_code(W, j, k, depth + 1)
            }
            return 1
        }
        return 1
    }
    # an interpreter: python/perl/ruby/node/Rscript/R
    for (j = i + 1; j <= k; j++) {
        v = W[j]
        if (v == "") continue
        if (v == "-" || v ~ /^-[A-Za-z]*[ce]$/) return 1
        if (v ~ /^[0-9]*[<>]/ || v ~ /^&>/ || v ~ /^<</) continue
        if (v ~ /^-/) continue
        return 0
    }
    return 1
}

function pipes_into_runner(str,   t, seg, k, W, i, w, wrapped) {
    t = str
    while (match(t, /\|&?[ \t]*/)) {
        seg = substr(t, RSTART + RLENGTH)
        t = seg
        sub(/[|;&\n].*$/, "", seg)
        k = split(seg, W, /[ \t]+/)
        wrapped = 0
        for (i = 1; i <= k; i++) {
            w = W[i]
            if (w == "") continue
            if (w ~ /^[A-Za-z_][A-Za-z0-9_]*=/) continue
            if (is_runner(w)) { if (reads_code(W, i, k, 0)) return 1; break }
            if (w ~ /^(sudo|doas|env|command|exec|nohup|srun|ionice|nice|stdbuf|setsid|time|runuser|flock|timeout)$/) {
                wrapped = 1
                if (w == "timeout") i++
                continue
            }
            if (wrapped && w ~ /^-/) {
                if (w !~ /^--/ && w !~ /=/ && length(w) == 2 && i < k && W[i+1] !~ /^-/ && !is_runner(W[i+1])) i++
                continue
            }
            break
        }
    }
    return 0
}

# Does the text before `<<` hand the body to something that runs it?
# Any word of that segment counts, not only the first: `sudo -u bob bash`,
# `timeout 60 bash`, `srun bash` all hand the body to bash (#29, round 2).
# A writer's file name that merely contains one (`cat > bash_notes.md`) does
# not match, because the whole word must be the executor.
function executes(pre,   seg, k, i, w, W) {
    seg = pre
    # the segment that opens the here-doc: text after the last separator
    while (match(seg, /(\|\||&&|[|;&(])/)) seg = substr(seg, RSTART + RLENGTH)
    k = split(seg, W, /[ \t]+/)
    for (i = 1; i <= k; i++) {
        w = W[i]
        sub(/^\\/, "", w)
        sub(/^.*\//, "", w)
        if (w ~ /^(bash|sh|zsh|dash|ksh|ssh|on_site\.sh|python[0-9.]*|Rscript|R|perl|node|ruby|pwsh|powershell)$/) return 1
    }
    return 0
}

function scan(s,   m, d, isdash, pre, piped, out) {
    gsub(/<<</, "\001", s)
    # A `<<EOF` inside quotes (`grep -c '<<EOF' f`) is text, not a here-doc;
    # taken as one, it swallowed every line after it (#29, round 3). Quoted
    # DELIMITERS (`<<'EOF'`) are unquoted first so they survive, then every
    # other quoted string is dropped before looking for `<<`.
    out = ""
    while (match(s, /<<-?[ \t]*("[^"]*"|'[^']*')/)) {
        m = substr(s, RSTART, RLENGTH)
        gsub(/["']/, "", m)
        out = out substr(s, 1, RSTART - 1) m
        s = substr(s, RSTART + RLENGTH)
    }
    s = out s
    gsub(/'[^']*'/, "", s)
    gsub(/"[^"]*"/, "", s)
    pre = ""
    # `cat <<EOF | bash` hands the body to a shell through a pipe instead.
    piped = (s ~ /\|[ \t]*(sudo[ \t]+)?([^ \t|]*\/)?(bash|sh|zsh|dash|ksh|ssh)([ \t]|$)/) || pipes_into_runner(s)
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
