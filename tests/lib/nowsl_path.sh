# Sourced by the tests that fake a Git Bash (MSYS) host with no WSL bridge.
#
# nowsl_path <scratch-dir>  -> prints a PATH with every wsl.exe on it hidden
#
# Why: settings.sh decides "is the bridge there?" with `command -v wsl.exe`
# and a probe run. The MSYS fixtures fake `uname` but inherit the caller's
# PATH, so when the suite itself runs inside WSL - where Windows interop puts
# /mnt/c/WINDOWS/system32 (and often WindowsApps) on PATH - the real wsl.exe
# answers the probe, the "no bridge" cases test the bridge path instead, and
# they fail. CI never sees it: an ubuntu runner has no wsl.exe. Measured on
# a WSL2 laptop, 2026-09-27: on_site, session_start and wsl_bridge all red
# with interop on, all green with /mnt/* dropped from PATH.
#
# Same shape as nojq_path.sh: an entry holding wsl.exe is dropped outright
# when it has no shell in it (the Windows directories never do), and is
# otherwise swapped for a shim directory linking every OTHER binary, so the
# test never loses the bash it runs on. Fixtures that WANT a bridge put their
# own fake wsl.exe ahead of this PATH, as before.
#
# Returns 1 if wsl.exe is still reachable, so a "no bridge" case can never
# silently run with one.
nowsl_path() {
    local scratch="$1" out="" d shim i=0 f IFS=:
    for d in $PATH; do
        if [ -n "$d" ] && [ -x "$d/wsl.exe" ]; then
            if [ ! -x "$d/sh" ] && [ ! -x "$d/bash" ]; then
                continue
            fi
            i=$((i+1)); shim="$scratch/no_wsl_bin.$i"
            mkdir -p "$shim"
            for f in "$d"/*; do
                [ "$(basename "$f")" = wsl.exe ] && continue
                ln -sf "$f" "$shim/" 2>/dev/null
            done
            d="$shim"
        fi
        out="${out:+$out:}$d"
    done
    if PATH="$out" command -v wsl.exe >/dev/null 2>&1; then
        echo "nowsl_path: wsl.exe still reachable at $(PATH="$out" command -v wsl.exe)" >&2
        return 1
    fi
    printf '%s\n' "$out"
}
