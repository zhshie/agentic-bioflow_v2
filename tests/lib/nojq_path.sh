# Sourced by the hook tests that need a PATH on which jq cannot be found.
#
# nojq_path <scratch-dir>  -> prints a PATH with every jq on it hidden
#
# Dropping jq's directory from PATH is not safe: jq and bash usually share
# /usr/bin, so the hook would lose the shell it needs to start. Instead each
# PATH entry that holds a jq is swapped for a shim directory linking every
# OTHER binary in it.
#
# EVERY such entry, not just the first: on a usrmerge system (Ubuntu, and so
# the CI runner) /bin is a symlink to /usr/bin and both are on PATH, so hiding
# /usr/bin/jq alone still leaves /bin/jq. That once made every "no jq" case in
# CI test the with-jq path while passing on the cluster.
#
# Returns 1 if jq is still reachable afterwards, so a caller never runs a
# "no jq" case that silently has jq.
nojq_path() {
    local scratch="$1" out="" d shim i=0 f IFS=:
    for d in $PATH; do
        if [ -n "$d" ] && [ -x "$d/jq" ]; then
            i=$((i+1)); shim="$scratch/no_jq_bin.$i"
            mkdir -p "$shim"
            for f in "$d"/*; do
                [ "$(basename "$f")" = jq ] && continue
                ln -sf "$f" "$shim/" 2>/dev/null
            done
            d="$shim"
        fi
        out="${out:+$out:}$d"
    done
    if PATH="$out" command -v jq >/dev/null 2>&1; then
        echo "nojq_path: jq still reachable at $(PATH="$out" command -v jq)" >&2
        return 1
    fi
    printf '%s\n' "$out"
}
