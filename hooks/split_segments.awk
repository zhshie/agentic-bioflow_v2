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

function trim(s) { sub(/^[ \t\r]+/, "", s); sub(/[ \t\r]+$/, "", s); return s }

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
        s ~ /(^|[ \t\/])(python[0-9.]*|perl|ruby|node|Rscript)(\.exe)?([ \t]+-[^ \t]+)*[ \t]+-[A-Za-z]*[ce]([ \t]|$)/) {
        k = quoted(s)
        for (i = 1; i <= k; i++) qs[i] = QS[i]
        for (i = 1; i <= k; i++) split_cmd(qs[i], depth + 1)
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
    PIPED[depth] = force || (str ~ /\|&?[ \t]*((sudo|env|command|exec|nohup)[ \t]+)*([^ \t|]*\/)?(bash|sh|zsh|dash|ksh|pwsh|powershell)(\.exe)?([ \t]|$)/)
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
                k = index(substr(str, i + 1), "`")
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
            k = index(substr(str, i + 1), "`")
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
