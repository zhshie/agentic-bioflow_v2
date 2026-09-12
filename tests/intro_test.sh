#!/bin/bash
# scripts/intro.sh is the only thing allowed to say anything to a user at
# session start or command start - and it is only allowed to say what lives in
# scripts/intro/<lang>/*.txt. This tests the CLI surface from the plan's
# appendix ("附錄：2.7 的介面規格"): no-arg overview, per-command opening,
# --end's one-line signal, --list, --lang override, and the language fallback
# chain (settings file -> zh-TW, including when there is no settings file at
# all - a first-time user is exactly who needs this to still work).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
S="$ROOT/scripts/intro.sh"
fails=0

t()  { printf '%-62s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
has()    { printf '%-62s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: nothing matching '$2'"; fails=$((fails+1)); echo "---"; echo "$3"; echo "---"; }; }
hasnot() { printf '%-62s ' "$1"; grep -qF -- "$2" <<<"$3" && { echo "FAIL: found '$2', should not be there"; fails=$((fails+1)); } || echo ok; }

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
HOMEDIR="$TMP/home"; mkdir -p "$HOMEDIR"

# A clean run: no settings file reachable from anywhere. This is the state a
# first-time user is in, and intro.sh must still work - that is the entire
# point of an intro.
clean() { # clean [args...]
    env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE \
        HOME="$HOMEDIR" XDG_CONFIG_HOME="$TMP/nothing-here" \
        bash "$S" "$@"
}
clean_rc() { clean "$@" >"$TMP/out" 2>"$TMP/err"; echo $?; }

ZH_HEADINGS=("會做什麼" "你可以決定什麼" "不會做什麼" "結束時你會有什麼" "下一步")
EN_HEADINGS=("What it does" "What you decide" "What it will not do" "What you end up with" "Next step")

all_headings() { # all_headings <text> <heading...>
    local text="$1"; shift
    for h in "$@"; do grep -qF -- "$h" <<<"$text" || return 1; done
    return 0
}

# ---------------------------------------------------------------------------
# No settings file anywhere: default language must be zh-TW, silently.
echo "== no settings file at all: fallback to zh-TW =="

out="$(clean)"
rc="$(clean_rc)"
t "no-arg overview exits 0"                "$rc" "0"
has "overview mentions all five commands: setup" "setup" "$out"
has "overview mentions launch"             "launch" "$out"
has "overview mentions runs"               "runs" "$out"
has "overview mentions downstream"         "downstream" "$out"
has "overview mentions finish"             "finish" "$out"

out="$(clean setup)"
printf '%-62s ' "setup opening has all five zh-TW headings, no settings file"
if all_headings "$out" "${ZH_HEADINGS[@]}"; then echo ok; else
    echo "FAIL"; fails=$((fails+1))
fi

# ---------------------------------------------------------------------------
echo "== intro.sh <command> for each of the five, default language =="
for c in setup launch runs downstream finish; do
    out="$(clean "$c")"
    rc="$(clean_rc "$c")"
    t "intro.sh $c exits 0"                "$rc" "0"
    printf '%-62s ' "intro.sh $c has all five zh-TW headings"
    if all_headings "$out" "${ZH_HEADINGS[@]}"; then echo ok; else
        echo "FAIL"; fails=$((fails+1))
    fi
done

# ---------------------------------------------------------------------------
echo "== --end <command>: exactly one line, the flow-end signal =="
out="$(clean --end setup)"
rc="$(clean_rc --end setup)"
t "--end setup exits 0"                    "$rc" "0"
t "--end setup prints exactly one line"    "$(wc -l <<<"$out" | tr -d ' ')" "1"
t "--end setup prints the exact signal"    "$out" "flow-end: setup"

out="$(clean --end downstream)"
t "--end downstream names downstream, not setup" "$out" "flow-end: downstream"

# ---------------------------------------------------------------------------
echo "== --list: the command names that have opening text =="
out="$(clean --list)"
rc="$(clean_rc --list)"
t "--list exits 0"                         "$rc" "0"
for c in setup launch runs downstream finish; do
    has "--list names $c"                  "$c" "$out"
done

# ---------------------------------------------------------------------------
echo "== unknown command: usage on stderr, exit 2 =="
clean bogus-command >"$TMP/out" 2>"$TMP/err"; rc=$?
t "unknown command exits 2"                "$rc" "2"
t "unknown command prints nothing to stdout" "$(cat "$TMP/out")" ""
[ -s "$TMP/err" ]
t "unknown command prints usage to stderr" "$?" "0"

clean --end bogus-command >"$TMP/out" 2>"$TMP/err"; rc=$?
t "--end with an unknown command exits 2"  "$rc" "2"
t "--end with unknown command: no stdout"  "$(cat "$TMP/out")" ""

# ---------------------------------------------------------------------------
echo "== --lang override =="
out="$(clean --lang en setup)"
printf '%-62s ' "--lang en overrides default, all five en headings present"
if all_headings "$out" "${EN_HEADINGS[@]}"; then echo ok; else
    echo "FAIL"; fails=$((fails+1))
fi
hasnot "and none of the zh-TW headings leak into the en output" "會做什麼" "$out"

out="$(clean --lang en)"
printf '%-62s ' "--lang en overview is the en overview, not zh-TW"
if grep -qF "Next step" <<<"$out" && ! grep -qF "下一步" <<<"$out"; then echo ok; else
    echo "FAIL"; fails=$((fails+1))
fi

out="$(clean --lang zh-TW setup)"
printf '%-62s ' "--lang zh-TW is explicit and works the same as the default"
if all_headings "$out" "${ZH_HEADINGS[@]}"; then echo ok; else
    echo "FAIL"; fails=$((fails+1))
fi

# ---------------------------------------------------------------------------
echo "== language from the settings file =="
CONF="$TMP/xdg/agentic-bioflow"; mkdir -p "$CONF"
printf 'language: en\n' > "$CONF/env.yaml"
chmod 600 "$CONF/env.yaml"

with_en_settings() {
    env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE \
        HOME="$HOMEDIR" XDG_CONFIG_HOME="$TMP/xdg" \
        bash "$S" "$@"
}

out="$(with_en_settings setup)"
printf '%-62s ' "language: en in the settings file is picked up with no --lang"
if all_headings "$out" "${EN_HEADINGS[@]}"; then echo ok; else
    echo "FAIL"; fails=$((fails+1))
fi

out="$(with_en_settings --lang zh-TW setup)"
printf '%-62s ' "--lang still overrides a settings file that says en"
if all_headings "$out" "${ZH_HEADINGS[@]}"; then echo ok; else
    echo "FAIL"; fails=$((fails+1))
fi

# A settings file present, but with no language key at all - the missing-value
# case, distinct from the missing-file case tested above.
CONF2="$TMP/xdg2/agentic-bioflow"; mkdir -p "$CONF2"
printf 'workspace_id: 42\n' > "$CONF2/env.yaml"
chmod 600 "$CONF2/env.yaml"
out="$(env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE \
       HOME="$HOMEDIR" XDG_CONFIG_HOME="$TMP/xdg2" bash "$S" setup)"
printf '%-62s ' "settings file exists but has no language key: falls back to zh-TW"
if all_headings "$out" "${ZH_HEADINGS[@]}"; then echo ok; else
    echo "FAIL"; fails=$((fails+1))
fi

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failures"; exit 1; }
