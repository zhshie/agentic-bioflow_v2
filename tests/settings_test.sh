#!/bin/bash
# `settings.sh --set` exists for one situation: a script that ran on the site
# discovered where it put things, and the settings file that matters is on
# another machine. Its set_setting could only ever write to the file it can see.
#
# The comment-preserving behaviour is not cosmetic - the comments in a settings
# file are usually the only record of why a value is what it is.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/settings.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
F="$TMP/env.yaml"
fails=0
t() { printf '%-56s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }

run() { LAB_SETTINGS_FILE="$F" bash "$S" "$@"; }

run --set tw_bin /work/_bin/tw >/dev/null
t "--set writes a key that was not there"  "$(run tw_bin)"  "/work/_bin/tw"
t "and creates the file mode 600"          "$(stat -c %a "$F")" "600"

printf 'workspace_id: 111  # the one value a lab shares\n' >> "$F"
run --set workspace_id 222 >/dev/null
t "--set replaces an existing value"       "$(run workspace_id)" "222"
t "and keeps the comment saying why"       "$(grep -c 'the one value a lab shares' "$F")" "1"

t "a missing key still returns its default" "$(run nope fallback)" "fallback"


# ---------------------------------------------------------------------------
# Finding the file at all.
#
# The failure this prevents: with neither LAB_SETTINGS_FILE nor LAB_RUNS_DIR in
# the environment, the path resolved to the literal string `/_personal/env.yaml`
# - unreadable, but not an empty string. So every `setting` call returned its
# default in silence, `hooks/session_start.sh` stopped at its readability check,
# and a machine that was fully set up was indistinguishable from one that had
# never run setup. In a real session a member had to grep the filesystem to find
# their own config.
S_DIR="$(dirname "$S")"
HOMEDIR="$TMP/home"; mkdir -p "$HOMEDIR"

has()   { printf '%-56s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok \
          || { echo "FAIL: nothing matching '$2'"; fails=$((fails+1)); }; }
hasnot(){ printf '%-56s ' "$1"; grep -qF -- "$2" <<<"$3" \
          && { echo "FAIL: found '$2', which must never be printed"; fails=$((fails+1)); } || echo ok; }
hasre() { printf '%-56s ' "$1"; grep -qE -- "$2" <<<"$3" && echo ok \
          || { echo "FAIL: no line matching /$2/"; fails=$((fails+1)); }; }

# Neither of the two variables the old chain needed.
clean() { # clean <XDG_CONFIG_HOME> [args...]
  local x="$1"; shift
  env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE \
      HOME="$HOMEDIR" XDG_CONFIG_HOME="$x" bash "$S" "$@" 2>&1
}

XDG="$TMP/xdg"; CONF="$XDG/agentic-bioflow"; mkdir -p "$CONF"
cat > "$CONF/env.yaml" <<'YAML'
reach: local
site_user: sharedaccount
seqera_user: a-person
workspace_id: 424242
storage_root: /nowhere/runs
compute_env: ce-a-person
agent_connection: conn-a-person
YAML
chmod 600 "$CONF/env.yaml"

out=$(clean "$XDG" --summary)
has "--summary finds the file under XDG_CONFIG_HOME"   "$CONF/env.yaml"  "$out"
has "and says which file that was, before anything else" "settings file" "$out"
has "and names the site account"                       "sharedaccount"   "$out"
has "and the Seqera account, which is who a person is here" "a-person"   "$out"
has "and the workspace"                                "424242"          "$out"
has "and the run area"                                 "/nowhere/runs"   "$out"
has "and the compute environment"                      "ce-a-person"     "$out"
has "and the outputs reader's connection"              "conn-a-person"   "$out"

out=$(clean "$XDG" seqera_user)
t "a plain read finds the XDG file too" "$out" "a-person"

# With nothing anywhere, the error has to name the places it looked. Naming one
# unreadable path is what sent a member grepping.
out=$(clean "$TMP/nothing-here" --summary)
has "with nothing anywhere, names the XDG place searched" \
    "$TMP/nothing-here/agentic-bioflow/env.yaml" "$out"
hasnot "and never the bare /_personal path the old chain built" "/_personal" "$out"

out=$(env -u LAB_SETTINGS_FILE -u SEQERA_TOKEN_FILE LAB_RUNS_DIR="$TMP/norun" \
        HOME="$HOMEDIR" XDG_CONFIG_HOME="$TMP/nothing-here" bash "$S" --summary 2>&1)
has "and names the run area it searched when there is one" \
    "$TMP/norun/_personal/env.yaml" "$out"

# ---------------------------------------------------------------------------
# The token is the one thing a summary may never say. "Never printed, never in
# git, never in a params file" is the rule the whole setup is built around, and
# a convenience command that leaks it is worse than no convenience command.
SECRET='not-a-real-token-but-treat-it-as-one-9Q7X'
printf '%s\n' "$SECRET" > "$CONF/.seqera_token"; chmod 600 "$CONF/.seqera_token"
out=$(clean "$XDG" --summary)
hasnot "--summary never prints the token itself"       "$SECRET"            "$out"
has    "but does say it is there, and still protected" "present (mode 600)" "$out"

chmod 644 "$CONF/.seqera_token"
out=$(clean "$XDG" --summary)
has    "and calls out a token the whole machine can read" "present but mode 644" "$out"
hasnot "still without printing it"                        "$SECRET"              "$out"
chmod 600 "$CONF/.seqera_token"

# ---------------------------------------------------------------------------
# `site_user` and the user half of `site_host` name one account, and a value
# written in two places drifts. It drifts silently: both readings still look
# right on the page. The check lives here rather than in preflight's own test
# because what it enforces is a settings-key contract - and a principle with no
# check is a slogan (docs/PRINCIPLES.md).
P="$S_DIR/preflight.sh"
printf '#!/bin/bash\nexit 0\n' > "$TMP/ssh"; chmod +x "$TMP/ssh"
printf '#!/bin/bash\nexit 0\n' > "$TMP/tw";  chmod +x "$TMP/tw"
: > "$TMP/pf.token"; chmod 600 "$TMP/pf.token"

pf() { printf '%s\n' "$@" > "$TMP/pf.yaml"
  LAB_SETTINGS_FILE="$TMP/pf.yaml" SEQERA_TOKEN_FILE="$TMP/pf.token" \
  ON_SITE_SSH_BIN="$TMP/ssh" TW_BIN="$TMP/tw" bash "$P" 2>&1; }

out=$(pf 'reach: ssh' 'site_host: someone@site.example' 'site_user: somebody-else' \
         'storage_root: /nowhere/runs' 'workspace_id: 1' 'compute_env: ce')
hasre "preflight FAILs when site_user and site_host disagree" '^FAIL +site-user' "$out"
has   "and shows the value that has to change"               'somebody-else'    "$out"

out=$(pf 'reach: ssh' 'site_host: someone@site.example' 'site_user: someone' \
         'storage_root: /nowhere/runs' 'workspace_id: 1' 'compute_env: ce')
hasre "and passes when the two agree"                        '^OK +site-user'   "$out"

echo

# ---------------------------------------------------------------------------
# Two homes on one machine.
#
# The failure this prevents, measured on a real laptop: setup was done in WSL
# (commands/setup.md requires it - PITFALLS 16b), and Claude Code's Bash tool
# runs Git Bash. Different $HOME, a filesystem the other shell cannot read, and
# an export in WSL's ~/.bashrc that this shell never sees. Every candidate path
# is truthfully absent and the settings file is truthfully there, so the search
# report above is correct and useless. The note has to name the second home, or
# "not set up" is the only reading available.
UB="$TMP/ubin"; mkdir -p "$UB"
printf '#!/bin/sh\necho MINGW64_NT-10.0-22631\n' > "$UB/uname"; chmod +x "$UB/uname"

msys() { env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE \
             HOME="$HOMEDIR" XDG_CONFIG_HOME="$TMP/nowhere" PATH="$UB:$PATH" \
             bash "$S" "$@" 2>&1; }

out=$(msys workspace_id --required)
has   "under MSYS the miss names the second home"      "Git Bash/MSYS"      "$out"
has   "and says a WSL setup is invisible from here"    "not visible from here" "$out"
has   "and sends them to WSL, not to moving the file"  "PITFALLS 16b"       "$out"
has   "while still listing where it looked"            "No settings file"   "$out"

# The note is only true on Windows. Printed anywhere else it is noise, and a
# hint that fires everywhere teaches the reader to skip the whole block.
out=$(clean "$TMP/nowhere" workspace_id --required)
hasnot "on Linux there is no second home, so no note"  "Git Bash/MSYS"      "$out"
has    "and the ordinary search report is unchanged"   "No settings file"   "$out"

# ---------------------------------------------------------------------------
# Steered past a real file.
#
# All three ways "no settings file" gets printed wrongly are caused by a
# variable being set - two homes on one machine, an rc file this shell does not
# read, or a path written under a $LAB_RUNS_DIR that has since left the
# environment. The default with no variables at all is already correct
# everywhere. So the message must not recommend setting one, and when the real
# file is sitting at that default it has to say so: that is the only form of
# this failure a person can fix in one command.
STEER="$TMP/steer"; mkdir -p "$STEER/.config/agentic-bioflow"
cat > "$STEER/.config/agentic-bioflow/env.yaml" <<'YAML'
seqera_user: steered
YAML
out=$(env -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE HOME="$STEER" \
          XDG_CONFIG_HOME="$STEER/.config" \
          LAB_SETTINGS_FILE="$TMP/gone/env.yaml" bash "$S" seqera_user --required 2>&1)
has "a variable pointing nowhere is told the real file exists" \
    "BUT a settings file exists at" "$out"
has "and names it on that line, not just in the advice" \
    "exists at $STEER/.config/agentic-bioflow/env.yaml" "$out"
has "and says which variable to unset"  "Unset LAB_SETTINGS_FILE"  "$out"

# Absence has to stay absence. A line that fires when there is genuinely
# nothing there would send the reader looking for a file that does not exist.
out=$(clean "$TMP/nowhere" seqera_user --required)
hasnot "with nothing anywhere, no phantom file is announced" \
       "BUT a settings file exists"  "$out"

# The closing advice used to name LAB_SETTINGS_FILE, i.e. the hazard itself.
out=$(clean "$TMP/nowhere" seqera_user --required)
has    "the advice names the no-variable default"  "/agentic-bioflow/env.yaml"  "$out"
hasnot "and no longer recommends setting a variable" \
       "point LAB_SETTINGS_FILE at an existing one"  "$out"


# ---------------------------------------------------------------------------
# Which startup file an export goes into.
#
# `~/.bashrc` was hardcoded. On macOS the default shell is zsh, which never
# reads it: the export vanishes with no error and the next terminal looks
# unconfigured - PITFALLS 25's symptom on a machine with one home directory and
# therefore no clue to follow. The file and the syntax have to be decided
# together, because getting either one wrong fails silently.
pf() { SHELL="$1" HOME=/home/me ZDOTDIR="" bash "$S" --profile-file; }
px() { SHELL="$1" HOME=/home/me bash "$S" --profile-export LAB_RUNS_DIR /work/runs; }

t "bash gets .bashrc"        "$(pf /bin/bash)"      "/home/me/.bashrc"
t "zsh gets .zshrc, not .bashrc" "$(pf /usr/bin/zsh)" "/home/me/.zshrc"
t "fish gets its own config" "$(pf /usr/bin/fish)"  "/home/me/.config/fish/config.fish"
t "tcsh gets .cshrc"         "$(pf /bin/tcsh)"      "/home/me/.cshrc"
t "an unknown shell gets the POSIX answer" "$(pf /opt/x/oil)" "/home/me/.profile"
t "ZDOTDIR moves zsh's file"  "$(SHELL=/usr/bin/zsh HOME=/home/me ZDOTDIR=/etc/z bash "$S" --profile-file)" "/etc/z/.zshrc"

# The syntax has to match the file it is written into.
t "bash gets export"   "$(px /bin/bash)"     'export LAB_RUNS_DIR="/work/runs"'
t "fish gets set -gx"  "$(px /usr/bin/fish)" 'set -gx LAB_RUNS_DIR /work/runs'
t "tcsh gets setenv"   "$(px /bin/tcsh)"     'setenv LAB_RUNS_DIR "/work/runs"'

[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
