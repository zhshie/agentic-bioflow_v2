# Split a shell command into the simple commands it will run, one per line:
#
#     <segment as written>\037<the same segment with quoted text removed>\037<command word>
#
# Shared by hooks/confirm_cleanup.sh and hooks/launch_trigger.sh (#29), so the
# two gates cannot disagree about what a command line contains. The earlier
# versions each carried their own sed split, and each lost commands in the
# same places: text inside quotes (deleted to stop `grep 'a|rm b'` from reading
# as a delete), `$(...)`, backticks and `<(...)` (never looked inside), and
# strings a second interpreter re-reads (`bash -c '...'`, `perl -e
# 'system("...")'`, `python3 -c "os.system('...')"`, `echo '...' | bash`).
# Every one of those passed a real delete or launch with nothing printed.
#
# What this does instead:
#   - splits on ; | & && || newlines and subshell ( ) only OUTSIDE quotes;
#     `>&` and `&>` are redirects, not separators;
#   - keeps quoted text in the first column (a target is often quoted) and
#     drops it from the second (a verb inside a quoted regex is not a verb);
#   - drops `# comments` that start a word outside quotes;
#   - also emits, as commands of their own, the contents of $(...), `...`,
#     <(...) and >(...), and of every quoted string a shell or interpreter
#     will re-read: after bash/sh -c, eval, ssh, on_site.sh, powershell/pwsh,
#     python/perl/ruby/node/Rscript -c/-e, on a line that pipes into a shell,
#     and inside a code call like system(...) / subprocess.run([...]), where
#     the quoted strings are emitted one by one and joined by spaces
#     (["tw", "launch", "x"] -> tw launch x).
#
# Over-splitting is the safe direction: a stray quote or a multi-line string
# can only produce extra segments, never hide one. If awk itself is missing,
# the callers fall back to their old splitting and say so in their comments.

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

# #62: the text after each pipe comes from one split on the pipes, not from a
# copy of the rest of the string at every pipe - that was quadratic in the
# number of pipes (39 s for a 100 KB script of pipelines under Git Bash). A piece
# is the text between two pipes; cut at the first ; & or newline it is what
# followed the pipe up to the end of that command, as before.
function pipes_into_runner(str,   n, P, p, seg, k, W, i, w, wrapped) {
    n = split(str, P, /\|&?/)
    for (p = 2; p <= n; p++) {
        seg = P[p]
        sub(/[;&\n].*$/, "", seg)
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

function trim(s) { sub(/^[ \t\r]+/, "", s); sub(/[ \t\r]+$/, "", s); return s }

# How far after position i the next backtick is (what index(substr(str, i + 1),
# "`") gave), or 0 - scanned forward rather than copying the rest of the string
# at every backtick, which was quadratic (#62). n is length(str).
function next_tick(str, i, n,   j) {
    for (j = i + 1; j <= n; j++) if (substr(str, j, 1) == "`") return j - i
    return 0
}

# Index of the ")" closing the "(" at position p, or 0.
function close_paren(str, p,   n, d, i, c, q) {
    n = length(str); d = 0; q = ""
    for (i = p; i <= n; i++) {
        c = substr(str, i, 1)
        if (q != "") { if (c == q) q = ""; else if (c == "\\" && q == "\"") i++; continue }
        if (c == "'" || c == "\"") { q = c; continue }
        if (c == "\\") { i++; continue }
        if (c == "(") d++
        else if (c == ")") { d--; if (d == 0) return i }
    }
    return 0
}

# Fill QS[1..k] with the contents of the top-level quoted strings of s.
function quoted(s,   n, i, c, q, cur, k) {
    n = length(s); q = ""; cur = ""; k = 0
    for (i = 1; i <= n; i++) {
        c = substr(s, i, 1)
        if (q == "") {
            if (c == "\\") { i++; continue }
            if (c == "'" || c == "\"") { q = c; cur = "" }
            continue
        }
        if (c == q) { QS[++k] = cur; q = ""; continue }
        if (q == "\"" && c == "\\" && i < n) { cur = cur substr(s, i + 1, 1); i++; continue }
        cur = cur c
    }
    return k
}

# The command word, lowercased: past sudo/env/command/exec/nohup/time/nice/
# timeout and their options, VAR=value, quote characters (`"/bin/rm"`), a
# leading backslash (`\rm` skips an alias) and a directory (`/bin/rm`).
function cmdword(s,   k, W, i, w) {
    gsub(/["']/, "", s)
    k = split(s, W, /[ \t]+/); i = 1
    while (i <= k) {
        w = W[i]
        if (w == "") { i++; continue }
        if (w ~ /^(sudo|env|command|builtin|exec|nohup|time|nice|stdbuf)$/) { i++; continue }
        if (w == "timeout") { i += 2; continue }
        if (w ~ /^-(u|g|n|C|p)$/) { i += 2; continue }
        if (w ~ /^-/) { i++; continue }
        if (w ~ /^[A-Za-z_][A-Za-z0-9_]*=/) { i++; continue }
        break
    }
    w = (i <= k) ? W[i] : ""
    sub(/^\\/, "", w)
    sub(/^.*\//, "", w)
    w = tolower(w)
    sub(/\.exe$/, "", w)
    return w
}

function emit(seg, vs, depth,   s, v, k, i, joined, qs, ps, pv) {
    s = trim(seg); v = trim(vs)
    if (s == "") return
    # One segment is one output line: a newline inside a quoted argument
    # would otherwise split it, and the reader would see half a command.
    ps = s; pv = v
    gsub(/\n/, " ", ps); gsub(/\n/, " ", pv)
    print ps "\037" pv "\037" cmdword(ps)
    if (depth >= MAXDEPTH) return
    # Options may come before -c/-e (`bash -e -c`, `bash --norc -c`,
    # `python3 -u -c`, `perl -MFile::Path -e`), and `<<<` hands a string to
    # an interpreter just as -c does (#29, round 3).
    if (PIPED[depth] ||
        s ~ /(^|[ \t\/])(bash|sh|zsh|ksh|dash)([ \t]+-[^ \t]+)*[ \t]+-[A-Za-z]*c([ \t]|$)/ ||
        s ~ /(^|[ \t\/])(bash|sh|zsh|ksh|dash|python[0-9.]*|perl|ruby|node|Rscript|pwsh|powershell)(\.exe)?([ \t]+[^ \t<]+)*[ \t]*<<</ ||
        s ~ /(^|[ \t])eval([ \t]|$)/ ||
        s ~ /(^|[ \t\/])(ssh|on_site\.sh)([ \t]|$)/ ||
        s ~ /(^|[ \t\/])(powershell|pwsh)(\.exe)?([ \t]|$)/ ||
        s ~ /(^|[ \t\/])(python[0-9.]*|perl|ruby|node|Rscript|R)(\.exe)?([ \t]+-[^ \t]+)*[ \t]+-[A-Za-z]*[ce]([ \t]|$)/ ||
        # #35: other things that hand a string to a shell - `flock l -c '...'`,
        # `su lab -c '...'`, `tmux new 'cmd'`, `tmux send-keys 'cmd' Enter`,
        # `screen -X stuff 'cmd'`. Reading their quoted text as commands can
        # only add segments, never hide one.
        s ~ /(^|[ \t\/])(flock|su|runuser|sg)([ \t]+[^ \t]+)*[ \t]+-[A-Za-z]*c([ \t]|$)/ ||
        s ~ /(^|[ \t\/])(tmux|screen)([ \t]|$)/) {
        k = quoted(s)
        for (i = 1; i <= k; i++) qs[i] = QS[i]
        for (i = 1; i <= k; i++) split_cmd(qs[i], depth + 1)
    }
    # #35: `a=(rm -rf results); "${a[@]}"` - the words of an array assignment
    # may be a command. Read the inside as one.
    if (match(s, /^[A-Za-z_][A-Za-z0-9_]*=\(/)) {
        k = RLENGTH
        joined = substr(s, k + 1)
        sub(/\)[ \t]*$/, "", joined)
        split_cmd(joined, depth + 1)
    }
    if (s ~ /(system|popen|Popen|subprocess\.[a-z_]+|exec[lvpe]*|spawn[a-z]*|check_(output|call)|run)[ \t]*\(/) {
        k = quoted(s); joined = ""
        for (i = 1; i <= k; i++) qs[i] = QS[i]
        for (i = 1; i <= k; i++) { split_cmd(qs[i], depth + 1); joined = joined (i > 1 ? " " : "") qs[i] }
        if (k > 1) split_cmd(joined, depth + 1)
    }
}

# force: the caller knows a shell reads this text (`bash <(echo '...')`), so
# every quoted string in it is a command too.
function split_cmd(str, depth, force,   n, i, c, nx, pv, q, seg, vs, k, sub_d, rd) {
    if (depth > MAXDEPTH) {
        # Too deep to read. Say so rather than stop silently (invariant 13):
        # the gates treat this marker as a command they could not judge.
        print "(nested too deeply to read)\037(nested too deeply to read)\037__too_deep__"
        return
    }
    PIPED[depth] = force || (str ~ /\|&?[ \t]*((sudo|env|command|exec|nohup)[ \t]+)*([^ \t|]*\/)?(bash|sh|zsh|dash|ksh|pwsh|powershell)(\.exe)?([ \t]|$)/) || pipes_into_runner(str)
    n = length(str); q = ""; seg = ""; vs = ""
    for (i = 1; i <= n; i++) {
        c = substr(str, i, 1); nx = substr(str, i + 1, 1); pv = (i > 1) ? substr(str, i - 1, 1) : ""
        if (q == "'") { seg = seg c; if (c == "'") q = ""; continue }
        if (c == "\\" && nx == "\n") { i++; continue }             # line continuation
        if (c == "\\" && i < n) { seg = seg c nx; if (q == "") vs = vs c nx; i++; continue }
        if (q == "\"") {
            if (c == "\"") { q = ""; seg = seg c; continue }
            if (c == "$" && nx == "(") {
                k = close_paren(str, i + 1)
                if (k) { split_cmd(substr(str, i + 2, k - i - 2), depth + 1); seg = seg substr(str, i, k - i + 1); i = k; continue }
            }
            if (c == "`") {
                k = next_tick(str, i, n)
                if (k) { split_cmd(substr(str, i + 1, k - 1), depth + 1); seg = seg substr(str, i, k + 1); i += k; continue }
            }
            seg = seg c; continue
        }
        # outside quotes
        if (c == "'" || c == "\"") { q = c; seg = seg c; continue }
        if (c == "#" && (i == 1 || pv ~ /[ \t;&|(\n]/)) {
            while (i <= n && substr(str, i, 1) != "\n") i++
            emit(seg, vs, depth); seg = ""; vs = ""; continue
        }
        if ((c == "$" || c == "<" || c == ">") && nx == "(") {
            k = close_paren(str, i + 1)
            if (k) {
                # `bash <(echo '...')` / `source <(...)`: a shell reads what
                # the substitution prints, so its quoted strings are commands.
                rd = (c == "<" && seg ~ /(^|[ \t\/])(bash|sh|zsh|dash|ksh|source|\.)[ \t]+$/)
                split_cmd(substr(str, i + 2, k - i - 2), depth + 1, rd)
                seg = seg substr(str, i, k - i + 1); vs = vs substr(str, i, k - i + 1); i = k; continue
            }
        }
        if (c == "`") {
            k = next_tick(str, i, n)
            if (k) { split_cmd(substr(str, i + 1, k - 1), depth + 1); seg = seg substr(str, i, k + 1); vs = vs substr(str, i, k + 1); i += k; continue }
        }
        if (c == "&" && (pv == ">" || nx == ">")) { seg = seg c; vs = vs c; continue }
        # ( ) split only as a subshell: `(cd x && rm y)`. After a word it is a
        # call - system("...") - and the call must stay one piece to be read.
        if (c == "(" && (i == 1 || pv ~ /[ \t;&|(\n]/)) { sub_d++; emit(seg, vs, depth); seg = ""; vs = ""; continue }
        if (c == ")" && sub_d > 0) { sub_d--; emit(seg, vs, depth); seg = ""; vs = ""; continue }
        if (c == "\n" || c == ";" || c == "|" || c == "&") {
            emit(seg, vs, depth); seg = ""; vs = ""; continue
        }
        seg = seg c; vs = vs c
    }
    emit(seg, vs, depth)
}

BEGIN { MAXDEPTH = 8 }
{ ALL = ALL (NR > 1 ? "\n" : "") $0 }
END { split_cmd(ALL, 0, 0) }
