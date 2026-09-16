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
has   "and says the mode it prints there is manufactured"  "PITFALLS 16j"  "$out"
hasnot "without repeating the retracted conclusion"    "only WSL can hold"  "$out"
has   "while still listing where it looked"            "No settings file"   "$out"

# A3: the advice here used to stop at "start Claude Code from a WSL shell",
# leaving unsaid the part a member actually needs - that the PROJECT folder
# they already work in does not have to move anywhere. That half stands.
has   "and says the project folder itself does not have to move" "does not have to move" "$out"

# The other half of A3 did not. It told the member to move the SHELL, and
# named /mnt/c as the way back to their folder afterwards; 2.13 removed the
# move, so naming the way back would only put it there again. And its claim
# that the settings file has to live in the WSL home stopped being true the
# moment the scripts kept running in this shell - where the file ends up is
# not predicted here, it is measured at write time.
hasnot "and no longer sends the member to another shell" "from a WSL shell"    "$out"
has   "and points at the write-time check instead"      "reads that back" "$out"

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

# ---------------------------------------------------------------------------
# D5: `--set` refuses a write shaped like the site's path under `reach: ssh`.
#
# The measured failure (docs/SETTINGS.md): a laptop with a leftover
# LAB_RUNS_DIR exported writes its settings file into
# "$LAB_RUNS_DIR/_personal/env.yaml" - a directory that looks exactly like the
# site's, but is local, and the next shell (with the variable gone again)
# cannot find it.
D5HOME="$TMP/d5home"; mkdir -p "$D5HOME"
# Every case below is exercised through the SAME candidate resolution a real
# broken laptop hits: no LAB_SETTINGS_FILE at all, so LAB_RUNS_DIR is free to
# steer where set_setting would write, exactly as docs/SETTINGS.md describes.
RD="$TMP/d5_site_runs"

printf '%-64s ' "bootstrapping reach:ssh itself is refused when LAB_RUNS_DIR leaks in"
out=$(env -u LAB_SETTINGS_FILE HOME="$D5HOME" XDG_CONFIG_HOME="$D5HOME/xdg1" \
          LAB_RUNS_DIR="$RD" bash "$S" --set reach ssh 2>&1); rc=$?
[ "$rc" = 2 ] && grep -qiF "LAB_RUNS_DIR" <<<"$out" && echo ok \
  || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
printf '%-64s ' "...and names the XDG location settings belong at"
grep -qF "agentic-bioflow/env.yaml" <<<"$out" && echo ok \
  || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }
printf '%-64s ' "...and creates nothing at all"
[ ! -e "$RD/_personal/env.yaml" ] && [ ! -e "$D5HOME/xdg1/agentic-bioflow/env.yaml" ] && echo ok \
  || { echo "FAIL: a file appeared somewhere"; fails=$((fails+1)); }

# A settings file already exists at the XDG default recording reach: ssh -
# now a later --set call, with LAB_RUNS_DIR leaking into THIS shell too, must
# also be refused, even though the write itself is not to the `reach` key.
XDG2="$D5HOME/xdg2"; mkdir -p "$XDG2/agentic-bioflow"
cat > "$XDG2/agentic-bioflow/env.yaml" <<'YAML'
reach: ssh
site_host: me@example.org
YAML
chmod 600 "$XDG2/agentic-bioflow/env.yaml"
before_sum=$(md5sum "$XDG2/agentic-bioflow/env.yaml")

printf '%-64s ' "a later --set is refused too, once reach:ssh is already recorded"
out=$(env -u LAB_SETTINGS_FILE HOME="$D5HOME" XDG_CONFIG_HOME="$XDG2" \
          LAB_RUNS_DIR="$RD" bash "$S" --set workspace_id 12345 2>&1); rc=$?
[ "$rc" = 2 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
printf '%-64s ' "...and the real settings file is untouched"
after_sum=$(md5sum "$XDG2/agentic-bioflow/env.yaml")
[ "$before_sum" = "$after_sum" ] && echo ok || { echo "FAIL: file changed"; fails=$((fails+1)); }
printf '%-64s ' "...and nothing was written under LAB_RUNS_DIR either"
[ ! -e "$RD/_personal/env.yaml" ] && echo ok || { echo "FAIL: site-shaped file appeared"; fails=$((fails+1)); }

# --- every other case keeps working exactly as before ----------------------
printf '%-64s ' "reach:local with LAB_RUNS_DIR set is NOT refused - that is the normal site case"
XDG3="$D5HOME/xdg3"; mkdir -p "$XDG3"
out=$(env -u LAB_SETTINGS_FILE HOME="$D5HOME" XDG_CONFIG_HOME="$XDG3" \
          LAB_RUNS_DIR="$RD/local-ok" bash "$S" --set reach local 2>&1); rc=$?
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }

printf '%-64s ' "no reach recorded and LAB_RUNS_DIR set defaults to local - NOT refused"
XDG4="$D5HOME/xdg4"; mkdir -p "$XDG4"
out=$(env -u LAB_SETTINGS_FILE HOME="$D5HOME" XDG_CONFIG_HOME="$XDG4" \
          LAB_RUNS_DIR="$RD/plain" bash "$S" --set workspace_id 1 2>&1); rc=$?
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }

printf '%-64s ' "reach:ssh but LAB_RUNS_DIR unset is NOT refused - nothing to be steered by"
XDG5="$D5HOME/xdg5"; mkdir -p "$XDG5/agentic-bioflow"
printf 'reach: ssh\n' > "$XDG5/agentic-bioflow/env.yaml"; chmod 600 "$XDG5/agentic-bioflow/env.yaml"
out=$(env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR HOME="$D5HOME" XDG_CONFIG_HOME="$XDG5" \
          bash "$S" --set workspace_id 1 2>&1); rc=$?
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }

printf '%-64s ' "an explicit LAB_SETTINGS_FILE always wins, even with LAB_RUNS_DIR set"
EXPLICIT="$TMP/d5_explicit.yaml"
out=$(LAB_SETTINGS_FILE="$EXPLICIT" LAB_RUNS_DIR="$RD" bash "$S" --set reach ssh 2>&1); rc=$?
[ "$rc" = 0 ] && [ -r "$EXPLICIT" ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }

echo

# ---------------------------------------------------------------------------
# B1: chmod 600 can be *accepted* and change nothing. /mnt/c under WSL without
# the 'metadata' mount option, and exFAT, both do this - no error, nothing a
# caller that only checks chmod's own exit code would ever see. A fake `chmod`
# that always succeeds but never actually changes a file's mode stands in for
# that filesystem: it is the one difference set_setting's read-back has to
# notice.
NOMODE="$TMP/nomode_bin"; mkdir -p "$NOMODE"
cat > "$NOMODE/chmod" <<'C'
#!/bin/bash
# Simulates a filesystem where chmod is accepted but silently does nothing.
exit 0
C
chmod +x "$NOMODE/chmod"

CANTHOLD="$TMP/canthold/env.yaml"
out=$(umask 022; PATH="$NOMODE:$PATH" LAB_SETTINGS_FILE="$CANTHOLD" \
      bash "$S" --set workspace_id 1 2>&1); rc=$?
printf '%-64s ' "a filesystem that cannot hold mode 600 is refused"
[ "$rc" = 1 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
has "...names the filesystems this actually happens on"    "/mnt/c" "$out"
has "...and exFAT"                                          "exFAT"  "$out"
has "...and says the token would be effectively public"     "effectively public" "$out"
printf '%-64s ' "...and the empty file it just made is gone again"
[ ! -e "$CANTHOLD" ] && echo ok \
  || { echo "FAIL: $CANTHOLD still exists"; fails=$((fails+1)); }

# 16k: under MSYS the manufactured mode must not decide anything by itself.
# 2.13.1 refused here - on a machine whose file was in fact owner-only - and
# then told the member to use a location under $HOME, naming the directory that
# had just "failed". With no way to ask Windows (no powershell.exe on this
# PATH) the honest answer is "cannot tell", which is what an unreadable stat
# already gets on every other platform. The case where Windows CAN be asked is
# tests/windows_privacy_test.sh.
out=$(umask 022; PATH="$NOMODE:$UB:$PATH" LAB_SETTINGS_FILE="$TMP/canthold2/env.yaml" \
      bash "$S" --set workspace_id 1 2>&1); rc=$?
t "under MSYS a manufactured mode alone never refuses" "$rc" "0"
hasnot "...and nothing is claimed about holding mode 600 there" "would not hold mode 600" "$out"
hasnot "...and it does not send them round the same circle" "under \$HOME instead" "$out"

# A file that already held real content before this call must never be
# deleted just because a later write's chmod did not hold - that would be a
# second, worse failure stacked on the first.
PREEXIST="$TMP/preexist/env.yaml"; mkdir -p "$(dirname "$PREEXIST")"
printf 'seqera_user: someone\n' > "$PREEXIST"; chmod 644 "$PREEXIST"
out=$(PATH="$NOMODE:$PATH" LAB_SETTINGS_FILE="$PREEXIST" \
      bash "$S" --set workspace_id 1 2>&1); rc=$?
printf '%-64s ' "a pre-existing settings file is still refused the same way"
[ "$rc" = 1 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
printf '%-64s ' "...but a file that already had content is never deleted"
grep -qF "someone" "$PREEXIST" 2>/dev/null && echo ok \
  || { echo "FAIL: pre-existing settings file was removed or emptied"; fails=$((fails+1)); }

# The ordinary case: a filesystem that DOES hold 600 is written exactly as
# before, and set_setting's own read-back does not get in the way of it.
CANHOLD="$TMP/canhold/env.yaml"
out=$(LAB_SETTINGS_FILE="$CANHOLD" bash "$S" --set workspace_id 1 2>&1); rc=$?
t "a filesystem that CAN hold 600 is written normally" "$rc" "0"
t "...at mode 600"                                      "$(stat -c %a "$CANHOLD")" "600"

# stat_mode itself can come back empty (its own documented case - see
# token_state()'s "" branch). That is "cannot tell", not "unsafe": a refusal
# triggered by a `stat` that simply answers differently would be worse than
# the silent-token bug this whole check exists to catch.
NOSTAT="$TMP/nostat_bin"; mkdir -p "$NOSTAT"
cat > "$NOSTAT/stat" <<'C'
#!/bin/bash
exit 1
C
chmod +x "$NOSTAT/stat"
CANTTELL="$TMP/canttell/env.yaml"
out=$(PATH="$NOSTAT:$PATH" LAB_SETTINGS_FILE="$CANTTELL" \
      bash "$S" --set workspace_id 1 2>&1); rc=$?
t "an unreadable mode ('cannot tell') is let through, not refused" "$rc" "0"

# ---------------------------------------------------------------------------
# B2: `--summary` used to print a hardcoded "mode 600" sentence, independent
# of whatever token_state() found two lines above it - the token's half of
# this file was already honest and the settings half was not. A fake `stat`
# that always reports a different mode proves --summary now reads it back the
# same way token_state() does, rather than asserting a constant.
FAKESTAT="$TMP/fakestat_bin"; mkdir -p "$FAKESTAT"
cat > "$FAKESTAT/stat" <<'C'
#!/bin/bash
echo 640
C
chmod +x "$FAKESTAT/stat"

SUMFILE="$TMP/summode/env.yaml"; mkdir -p "$(dirname "$SUMFILE")"
printf 'workspace_id: 1\n' > "$SUMFILE"; chmod 600 "$SUMFILE"
out=$(PATH="$FAKESTAT:$PATH" LAB_SETTINGS_FILE="$SUMFILE" bash "$S" --summary 2>&1)
has    "--summary prints the mode stat_mode actually reports" "$SUMFILE, mode 640" "$out"
hasnot "...never a hardcoded mode 600 for a file that isn't"  "$SUMFILE, mode 600" "$out"

# ---------------------------------------------------------------------------
# B3: a synced folder is a second, invisible risk chmod 600 cannot catch at
# all - mode 600 there is completely normal, and the sync client uploads the
# file to a third party anyway. Only the path's own name can hint at this.
out=$(clean "$TMP/OneDrive" --set workspace_id 1 2>&1); rc=$?
printf '%-64s ' "a synced-looking path is refused"
[ "$rc" = 2 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
has "...names the sync product it matched"      "OneDrive" "$out"
has "...says a token there would leave with the sync client" "third party" "$out"
has "...and says its own list is not complete"  "not a complete list" "$out"
printf '%-64s ' "...and creates nothing there at all"
[ ! -e "$TMP/OneDrive/agentic-bioflow/env.yaml" ] && echo ok \
  || { echo "FAIL: a file appeared under the synced folder"; fails=$((fails+1)); }

# Precedence matches site_shaped_write_refusal(): an explicit LAB_SETTINGS_FILE
# wins outright, because a member who named the location chose it deliberately.
EXPLICIT_SYNC="$TMP/OneDrive/chosen/env.yaml"
out=$(LAB_SETTINGS_FILE="$EXPLICIT_SYNC" bash "$S" --set workspace_id 1 2>&1); rc=$?
printf '%-64s ' "the same path is allowed when LAB_SETTINGS_FILE names it explicitly"
[ "$rc" = 0 ] && [ -r "$EXPLICIT_SYNC" ] && echo ok \
  || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }


# ---------------------------------------------------------------------------
# 2.13 Track B: set_setting() no longer shells out to python3 at all - it
# rewrites the `key: value` line with awk (PITFALLS 20c: Git Bash's python3 is
# a Microsoft Store stub that is on PATH, prints nothing, and exits 49; awk is
# POSIX and Git Bash ships it). Byte-identical behaviour is the bar, so these
# cases mirror what the old python block was relied on for.
BDIR="$TMP/b_awk"; mkdir -p "$BDIR"

# The assertion that proves the Windows case: with python3, python and py all
# shadowed by stubs that fail, set_setting must still write correctly. Real
# coreutils (awk, mkdir, chmod, stat, mv, mktemp...) stay on PATH after the
# shadow - only the three python names are intercepted, exactly like a Git
# Bash PATH where the only "python" on it is the unusable Store stub.
NOPY="$TMP/nopy_bin"; mkdir -p "$NOPY"
for name in python3 python py; do
    printf '#!/bin/bash\necho "%s: this stub must never run" >&2\nexit 49\n' "$name" > "$NOPY/$name"
    chmod +x "$NOPY/$name"
done
NOPYF="$BDIR/nopython.yaml"
out=$(PATH="$NOPY:$PATH" LAB_SETTINGS_FILE="$NOPYF" bash "$S" --set workspace_id 999 2>&1); rc=$?
printf '%-64s ' "set_setting writes correctly with no python3/python/py on PATH"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
t "...and the value reads back" \
  "$(PATH="$NOPY:$PATH" LAB_SETTINGS_FILE="$NOPYF" bash "$S" workspace_id)" "999"
hasnot "...and none of the shadow stubs ever ran" "this stub must never run" "$out"

# A rewrite must keep a key's trailing comment - it usually says why the
# value matters, and that's the one thing python's block was written to keep.
COMMENTF="$BDIR/comment.yaml"
printf 'site_user: old   # billed to this account\n' > "$COMMENTF"
LAB_SETTINGS_FILE="$COMMENTF" bash "$S" --set site_user new >/dev/null
t "a rewrite keeps the key's trailing comment" \
  "$(cat "$COMMENTF")" "site_user: new  # billed to this account"

# A file with no trailing newline gets one before the appended key - not a
# special case in the awk, just what `print` always terminates a record with.
NONLF="$BDIR/no_final_nl.yaml"
printf 'existing_key: 1' > "$NONLF"   # deliberately no trailing \n
LAB_SETTINGS_FILE="$NONLF" bash "$S" --set new_key added >/dev/null
t "a missing final newline is added before the appended key" \
  "$(cat "$NONLF")" "$(printf 'existing_key: 1\nnew_key: added')"
# `$(...)` strips trailing newlines on both sides of the comparison above, so
# it cannot tell "ends with \n" from "doesn't" - check that byte directly.
printf '%-64s ' "...and the appended line itself ends with a newline"
[ "$(tail -c1 "$NONLF" | wc -l)" -eq 1 ] && echo ok \
  || { echo "FAIL: $NONLF does not end with a newline"; fails=$((fails+1)); }

# Unrelated lines, comments and order survive a rewrite untouched - only the
# matched key's own line may change.
ORDERF="$BDIR/order.yaml"
printf 'a: 1\nb: 2  # keep me\nc: 3\n' > "$ORDERF"
LAB_SETTINGS_FILE="$ORDERF" bash "$S" --set b newval >/dev/null
t "unrelated lines, comments and order are untouched" \
  "$(cat "$ORDERF")" "$(printf 'a: 1\nb: newval  # keep me\nc: 3')"

# The 2.12 mode-600 readback refusal must still fire after the awk rewrite: a
# `stat` that reports 644 no matter what chmod just did must be refused, and a
# file THIS call created must not survive the refusal.
FAKESTAT644="$TMP/fakestat644_bin"; mkdir -p "$FAKESTAT644"
cat > "$FAKESTAT644/stat" <<'C'
#!/bin/bash
echo 644
C
chmod +x "$FAKESTAT644/stat"
REFUSEF="$BDIR/refuse.yaml"
out=$(PATH="$FAKESTAT644:$PATH" LAB_SETTINGS_FILE="$REFUSEF" bash "$S" --set workspace_id 1 2>&1); rc=$?
printf '%-64s ' "the 2.12 mode-600 refusal still fires (fake stat_mode 644)"
[ "$rc" = 1 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
printf '%-64s ' "...and the file this call created is not left behind"
[ ! -e "$REFUSEF" ] && echo ok || { echo "FAIL: $REFUSEF still exists"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
