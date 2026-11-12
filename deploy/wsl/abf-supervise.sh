#!/usr/bin/env bash
# abf-supervise.sh - keep the platform's processes running on a desktop WSL, and
# restart any that stops. Read from a list file, one process per line.
#
# Not systemd: a desktop WSL here has no systemd and no administrator rights; on a host that has
# systemd, use the user units in deploy/systemd/ instead of this script.
#
# Usage:
#   abf-supervise.sh [--list FILE]     run and watch every process in FILE (default below)
#   abf-supervise.sh --check [--list FILE]    only check FILE; start nothing; exit 2 on a problem
#   abf-supervise.sh --status          who is running now; exit 1 when the supervisor is not
#   abf-supervise.sh --stop            stop the running supervisor (SIGTERM) and wait until it is gone
#
# List file: ~/.config/abf-platform/processes (see deploy/wsl/processes.example), on the Linux file
# system (not under /mnt/). One process per line, "<name> [VAR=value ...] <program> [arguments]":
# "#" lines and blank lines are skipped; a name uses [a-z0-9-] and is unique; one line is one
# program (no && ; | chaining, no shell builtin such as cd). The program runs as `exec env VAR=value
# <program>` inside a login shell started in your home folder (so ~/.profile applies; the umask is
# the one this script inherited). Use absolute paths. The file must be owner-only (chmod 600). A
# token or password never goes in it: use --token-file. A line that looks like one (an abf_ token,
# a token, password, secret or pat word followed by = or a space and a value, user:password@ in a URL, a Bearer value, a private-key
# header) refuses the start; the message gives the line number, never the line.
#
# Exit codes: 0 ok (also "another supervisor is already running"); 1 --status and not running;
# 2 refused (bad list, bad rights, a token in the list, a missing tool, a folder that cannot be
# written); 129 stopped by SIGHUP (the window it ran in was closed) - non-zero on purpose, so the
# logon task's failure retry brings it back.
#
# Knobs (environment variables; the defaults are the real ones, the others exist for tests):
#   ABF_SUPERVISE_STATE   state folder       ~/.local/state/abf-platform
#   ABF_SUPERVISE_BASE    first interval, s  2        (doubles after each quick failure; > 0)
#   ABF_SUPERVISE_MAX     longest interval   60       (> 0)
#   ABF_SUPERVISE_STABLE  alive this long = healthy, the interval starts over   30
#   ABF_SUPERVISE_WAIT    on stop, wait this long for a child before SIGKILL    10
#   ABF_SUPERVISE_LOGMAX  rotate a log above this many bytes   10485760  (10 MB)
#   ABF_SUPERVISE_TICK    how often the logs are checked while running, s       5   (> 0)
# Numbers may have decimals (0.2).
#
# State folder (folder 0700, files 0600): supervise.lock, supervise.pid, supervise.log (the
# supervisor's own events, each line timestamped), log/<name>.log (a process's output; the
# last rotated one is <name>.log.1), proc/<name> (pid, times, counts - nothing else).
# The supervisor never reads a run's state and never prints the environment.
#
# Stop it with --stop, SIGTERM or Ctrl-C (it passes the signal on, waits, then SIGKILLs what is
# left). Do not just close its window (SIGHUP stops it, with exit 129). After a kill -9 the runners
# notice that it is gone, stop their processes and end by themselves within a few seconds.

set -u
ORIG_UMASK=$(umask)
umask 077

SELF=$0
SUPPID=$$
LIST_DEFAULT="${HOME:-}/.config/abf-platform/processes"
STATE="${ABF_SUPERVISE_STATE:-${HOME:-}/.local/state/abf-platform}"
case $STATE in /*) ;; *) STATE="$PWD/$STATE" ;; esac

say() { printf '%s\n' "$*"; }
err() { printf '%s\n' "$*" >&2; }

[ "${BASH_VERSINFO[0]:-0}" -ge 5 ] || { err "看守腳本需要 bash 5 以上（WSL 的 Ubuntu 22.04 有）；請用較新的 bash 再試。"; exit 2; }

to_us() { # "0.25" -> 250000; fails when it is not a plain non-negative number
    local v=$1
    [[ $v =~ ^([0-9]+)(\.([0-9]{1,6}))?$ ]] || return 1
    local i=${BASH_REMATCH[1]} f=${BASH_REMATCH[3]:-}
    f="${f}000000"; f=${f:0:6}
    printf '%s\n' $(( 10#$i * 1000000 + 10#$f ))
}
fmt_us() { # 400000 -> 0.4 ; 2000000 -> 2 ; a negative duration (a clock that stepped back) -> 0
    local us=$1 i f
    [ "$us" -lt 0 ] && us=0
    i=$(( us / 1000000 )); f=$(printf '%06d' $(( us % 1000000 )))
    while [[ $f == *0 ]]; do f=${f%0}; done
    if [ -n "$f" ]; then printf '%s.%s\n' "$i" "$f"; else printf '%s\n' "$i"; fi
}
now_us() { # NOW = microseconds on the monotonic clock (/proc/uptime), so a wall-clock step changes nothing
    local up
    if read -r up _ < /proc/uptime 2>/dev/null && [[ $up =~ ^([0-9]+)\.([0-9]{2})$ ]]; then
        NOW=$(( 10#${BASH_REMATCH[1]} * 1000000 + 10#${BASH_REMATCH[2]} * 10000 ))
    else
        NOW=${EPOCHREALTIME/[.,]/}
    fi
}
pid_alive() { # a process that exists and is not a zombie
    local l
    read -r l < "/proc/$1/stat" 2>/dev/null || return 1
    [[ $l == *') Z '* ]] && return 1
    return 0
}

[ -n "${HOME:-}" ] || { err "環境裡沒有 HOME，看守腳本不知道清單與記錄放哪；請從登入後的終端執行，或設好 HOME 再試。"; exit 2; }

MODE=run
LIST=""
while [ $# -gt 0 ]; do
    case $1 in
        --list) [ $# -ge 2 ] || { err "--list 後面要接清單檔的路徑；例如 --list <清單檔>。"; exit 2; }; LIST=$2; shift 2 ;;
        --check) MODE=check; shift ;;
        --status) MODE=status; shift ;;
        --stop) MODE=stop; shift ;;
        -h|--help) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$SELF"; exit 0 ;;
        *) err "不認得的選項「$1」；可用 --list、--check、--status、--stop，說明用 --help。"; exit 2 ;;
    esac
done
[ -n "$LIST" ] || LIST=$LIST_DEFAULT

for knob in BASE MAX STABLE WAIT TICK; do
    eval "raw=\${ABF_SUPERVISE_$knob:-}"
    [ -n "$raw" ] || continue
    if ! v=$(to_us "$raw"); then
        err "環境變數 ABF_SUPERVISE_$knob 要是不帶單位的數字（例如 2 或 0.5）；請改正或清掉它。"; exit 2
    fi
    case $knob in BASE|MAX|TICK)
        [ "$v" -gt 0 ] || { err "環境變數 ABF_SUPERVISE_$knob 要大於 0（0 會讓它空轉）；請改正或清掉它。"; exit 2; } ;;
    esac
done
BASE_US=$(to_us "${ABF_SUPERVISE_BASE:-2}")
MAX_US=$(to_us "${ABF_SUPERVISE_MAX:-60}")
STABLE_US=$(to_us "${ABF_SUPERVISE_STABLE:-30}")
WAIT_US=$(to_us "${ABF_SUPERVISE_WAIT:-10}")
TICK_US=$(to_us "${ABF_SUPERVISE_TICK:-5}")
LOGMAX=${ABF_SUPERVISE_LOGMAX:-10485760}
[[ $LOGMAX =~ ^[0-9]+$ ]] || { err "環境變數 ABF_SUPERVISE_LOGMAX 要是位元組數（整數）；請改正或清掉它。"; exit 2; }
[ "$MAX_US" -ge "$BASE_US" ] || MAX_US=$BASE_US

need_flock() {
    command -v flock >/dev/null 2>&1 || {
        err "這台機器缺 flock 這個工具，看守腳本沒有它就不能保證只跑一份；請先安裝（Ubuntu：apt install util-linux）再試。"
        exit 2
    }
}

on_windows_fs() { # a path that lives on a Windows drive (/mnt/c...): Linux cannot read its permissions truthfully
    local p d t
    p=$(readlink -f "$1" 2>/dev/null) || p=$1
    case $p in /mnt/*) ;; *) return 1 ;; esac
    d=$p
    while [ ! -e "$d" ] && [ "$d" != / ] && [ -n "$d" ]; do d=${d%/*}; done
    t=$(stat -f -c %T "${d:-/}" 2>/dev/null) || return 1
    case $t in 9p|v9fs|drvfs|fuseblk|fuse|ntfs|ntfs3|vfat|msdos|exfat|cifs|smb|smb2) return 0 ;; esac
    return 1
}

# ---------------------------------------------------------------- the list

NAMES=(); CMDS=(); NERR=0
bad() { err "$*"; NERR=$((NERR + 1)); }

secret_line() { # any line (comments too): does it carry something shaped like a secret? (never echoed)
    local l=$1 ll=${1,,}
    [[ $l =~ abf_[A-Za-z0-9_-]{40,} ]] && return 0
    [[ $ll =~ bearer[[:space:]]+[^[:space:]]{8,} ]] && return 0
    [[ $l == *'-----BEGIN'* ]] && return 0
    [[ $l =~ ://[^/[:space:]@]+:[^/[:space:]@]+@ ]] && return 0
    [[ $ll =~ (^|[^[:alnum:]])(token|password|secret|pat)=[^[:space:]] ]] && return 0
    return 1
}
secret_cmd() { # a command: "--token value" (a word, a space, a value); --token-file and the like are not this
    local ll=${1,,}
    [[ $ll =~ (^|[[:space:]-])(token|password|secret|pat)[[:space:]]+[^[:space:]-] ]] && return 0
    return 1
}

split_words() { # text -> WORDS (quotes taken off); META=1 when ; | & ` or $( stands outside quotes; QERR=1 on an open quote
    local s=$1 c cur="" q="" have=0 i prev=""
    WORDS=(); META=0; QERR=0
    for (( i = 0; i < ${#s}; i++ )); do
        c=${s:i:1}
        if [ "$q" = "'" ]; then
            if [ "$c" = "'" ]; then q=""; else cur+=$c; fi
        elif [ "$q" = '"' ]; then
            case $c in
                '"') q="" ;;
                '\') i=$((i + 1)); cur+=${s:i:1} ;;
                '`') META=1 ;;
                '$') [ "${s:i+1:1}" = "(" ] && META=1; cur+=$c ;;
                *) cur+=$c ;;
            esac
        else
            case $c in
                "'") q="'"; have=1 ;;
                '"') q='"'; have=1 ;;
                '\') i=$((i + 1)); cur+=${s:i:1}; have=1 ;;
                ' '|$'\t') if [ "$have" -eq 1 ]; then WORDS+=("$cur"); cur=""; have=0; fi ;;
                ';'|'|'|'`') META=1 ;;
                '&') case $prev in '<'|'>') ;; *) META=1 ;; esac; cur+=$c; have=1 ;;
                '$') [ "${s:i+1:1}" = "(" ] && META=1; cur+=$c; have=1 ;;
                *) cur+=$c; have=1 ;;
            esac
        fi
        prev=$c
    done
    [ -z "$q" ] || QERR=1
    [ "$have" -eq 1 ] && WORDS+=("$cur")
    return 0
}

program_of() { # WORDS -> PROG: the first word that is not VAR=value, ~ and $HOME filled in; empty when there is none
    local x
    PROG=""
    for x in "${WORDS[@]}"; do
        [[ $x =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] && continue
        case $x in
            '~/'*) x="$HOME/${x#'~/'}" ;;
            '$HOME/'*) x="$HOME/${x#'$HOME/'}" ;;
            '${HOME}/'*) x="$HOME/${x#'${HOME}/'}" ;;
        esac
        PROG=$x; return 0
    done
    return 0
}

load_list() { # fills NAMES CMDS, counts problems in NERR, says each one with its line number
    local f=$1 mode ln=0 line name cmd i exe
    NAMES=(); CMDS=(); NERR=0
    local -a lnos=()
    if [ ! -f "$f" ] || [ ! -r "$f" ]; then
        bad "找不到或讀不到清單檔 $f；請照 deploy/wsl/processes.example 建一份（chmod 600），或用 --list 指定位置。"
        return
    fi
    if on_windows_fs "$f"; then
        bad "清單檔 $f 在 Windows 的磁碟上（/mnt/ 底下），Linux 讀不準它的權限，所以不能用；請把它放在 Linux 檔案系統（例如家目錄底下）再用 --list 指定。"
        return
    fi
    mode=$(stat -c %a "$f" 2>/dev/null || echo 777)
    if [ $(( 8#$mode & 8#077 )) -ne 0 ]; then
        bad "清單檔 $f 的權限是 $mode，群組或其他人也能讀寫；它決定這個帳號會執行什麼，請先執行 chmod 600 $f。"
    fi
    while IFS= read -r line || [ -n "$line" ]; do
        ln=$((ln + 1))
        line=${line%$'\r'}
        [ "$ln" -eq 1 ] && line=${line#$'\xef\xbb\xbf'}
        # a secret-shaped string is refused on every line, comments included; the line is never echoed
        if secret_line "$line"; then
            bad "清單檔第 $ln 行像是權杖、密碼或金鑰（這裡不回印內容）；清單不放這些，請改用 --token-file（或 --password-file）指向放它的檔案。"
            continue
        fi
        line=${line#"${line%%[![:space:]]*}"}
        case $line in ''|'#'*) continue ;; esac
        name=${line%%[[:space:]]*}
        cmd=${line#"$name"}
        cmd=${cmd#"${cmd%%[![:space:]]*}"}
        case $name in
            *[!abcdefghijklmnopqrstuvwxyz0123456789-]*)
                bad "清單檔第 $ln 行：名字不合法，名字只能用小寫英文字母、數字與減號；請改名。"; continue ;;
        esac
        if [ -z "$cmd" ]; then
            bad "清單檔第 $ln 行：名字「$name」後面缺要執行的指令；請在名字後面接完整指令。"; continue
        fi
        for i in "${!NAMES[@]}"; do
            if [ "${NAMES[$i]}" = "$name" ]; then
                bad "清單檔第 ${lnos[$i]} 行與第 $ln 行的名字「$name」重複；每個名字只能用一次，請改其中一個。"
                continue 2
            fi
        done
        if secret_cmd "$cmd"; then
            bad "清單檔第 $ln 行像是帶著密碼或權杖的值（這裡不回印內容）；請改用 --token-file（或 --password-file）指向放它的檔案。"
            continue
        fi
        split_words "$cmd"
        if [ "$QERR" -eq 1 ]; then
            bad "清單檔第 $ln 行（$name）：引號沒有成對；請補齊引號。"; continue
        fi
        if [ "$META" -eq 1 ]; then
            bad "清單檔第 $ln 行（$name）：一行只能是一個程式與它的參數，不能用 &&、;、|、& 或 \$(...) 接幾個指令；要做幾件事，請寫進一支腳本再列那支腳本。"
            continue
        fi
        program_of
        exe=$PROG
        if [ -z "$exe" ]; then
            bad "清單檔第 $ln 行（$name）：只有環境設定（VAR=值），後面缺要執行的程式；請在後面接程式。"
        elif [[ $exe == *'$'* ]]; then
            :   # a variable in the program word cannot be checked here
        elif [[ $exe == */* ]]; then
            if [ ! -e "$exe" ]; then
                bad "清單檔第 $ln 行（$name）：找不到執行檔；請確認路徑，或先安裝它。"
            elif [ ! -f "$exe" ] || [ ! -x "$exe" ]; then
                bad "清單檔第 $ln 行（$name）：那個程式不可執行；請對它執行 chmod +x。"
            fi
        elif [ -z "$(type -P -- "$exe" 2>/dev/null)" ]; then
            case $(type -t -- "$exe" 2>/dev/null) in
                builtin|keyword)
                    bad "清單檔第 $ln 行（$name）：開頭那個字是 shell 內建指令，不是程式（例如 cd、export），一行只能是一個程式與它的參數；請改成程式，或把步驟寫進一支腳本。" ;;
                *)
                    bad "清單檔第 $ln 行（$name）：在 PATH 裡找不到執行檔；請改成完整路徑（登入工作的 PATH 很短）。" ;;
            esac
        fi
        NAMES+=("$name"); CMDS+=("$cmd"); lnos+=("$ln")
    done < "$f"
    if [ "$NERR" -eq 0 ] && [ "${#NAMES[@]}" -eq 0 ]; then
        bad "清單檔 $f 裡沒有可看守的行程（只有註解或空行）；請照 deploy/wsl/processes.example 加上要看守的行程。"
    fi
}

# ---------------------------------------------------------------- --status and --stop

if [ "$MODE" = status ]; then
    need_flock
    not_running() {
        say "看守腳本沒在跑。下一步：用 $SELF --list <清單檔> 手動試跑，或在 Windows 的工作排程器查登入工作 abf-platform-autostart。"
        exit 1
    }
    [ -f "$STATE/supervise.lock" ] || not_running
    exec 8<"$STATE/supervise.lock" || not_running
    if flock -n 8; then not_running; fi
    exec 8<&-
    spid=$(cat "$STATE/supervise.pid" 2>/dev/null || true)
    if ! [[ $spid =~ ^[0-9]+$ ]] || ! pid_alive "$spid"; then
        say "看守腳本本體已經不在，只剩收尾中的看守子殼，它們幾秒內會自己結束。請稍後再看一次，或用 $SELF --stop 等它們結束。"
        exit 1
    fi
    say "看守腳本在跑（行程編號 ${spid:-?}）。"
    shopt -s nullglob
    for pf in "$STATE"/proc/*; do
        [ -f "$pf" ] || continue
        pn=${pf##*/}; p_pid=""; p_start=""; p_n=0; p_run=0; p_fails=0
        while IFS='=' read -r k v; do
            case $k in pid) p_pid=$v ;; started) p_start=$v ;; restarts) p_n=$v ;; running) p_run=$v ;; fails) p_fails=$v ;; esac
        done < "$pf"
        extra=""
        [[ $p_fails =~ ^[0-9]+$ ]] && [ "$p_fails" -ge 5 ] && extra="  連續失敗 $p_fails 次（看 log/$pn.log）"
        if [ "$p_run" = 1 ] && [ -n "$p_pid" ] && pid_alive "$p_pid"; then
            say "$pn: 在跑  行程編號 $p_pid  上次啟動 $p_start  重啟次數 $p_n$extra"
        else
            say "$pn: 沒在跑（等著重啟）  行程編號 -  上次啟動 ${p_start:--}  重啟次數 $p_n$extra"
        fi
    done
    exit 0
fi

if [ "$MODE" = stop ]; then
    need_flock
    idle() { say "看守腳本本來就沒在跑，沒有要停的。"; exit 0; }
    [ -f "$STATE/supervise.lock" ] || idle
    exec 8<"$STATE/supervise.lock" || idle
    if flock -n 8; then idle; fi
    spid=$(cat "$STATE/supervise.pid" 2>/dev/null || true)
    if [[ $spid =~ ^[0-9]+$ ]] && pid_alive "$spid" && grep -qa 'abf-supervise' "/proc/$spid/cmdline" 2>/dev/null; then
        kill -TERM "$spid" 2>/dev/null
        say "已通知看守腳本（行程編號 $spid）停止，等它把行程收乾淨。"
    else
        say "看守腳本本體已經不在，只剩收尾中的看守子殼；等它們自己結束。"
    fi
    now_us; deadline=$(( NOW + WAIT_US + 20000000 ))
    while ! flock -n 8; do
        now_us
        if [ "$NOW" -ge "$deadline" ]; then
            err "等了很久看守腳本還沒停；請看 $STATE/supervise.log，必要時再執行一次 $SELF --stop。"
            exit 1
        fi
        sleep 0.2
    done
    say "看守腳本已停止。"
    exit 0
fi

# ---------------------------------------------------------------- --check and the start-up refusals

[ "$MODE" = run ] && need_flock
load_list "$LIST"
if [ "$NERR" -gt 0 ]; then
    err "清單有 $NERR 個問題，沒有啟動任何行程；請照上面逐行改好，再用 $SELF --check 確認。"
    exit 2
fi
if [ "$MODE" = check ]; then
    say "清單沒問題：${#NAMES[@]} 個行程，沒有啟動任何東西。"
    exit 0
fi
if on_windows_fs "$STATE"; then
    err "狀態資料夾 $STATE 在 Windows 的磁碟上（/mnt/ 底下），Linux 讀不準它的權限，所以沒有啟動任何行程；請放在 Linux 檔案系統（例如家目錄底下），用 ABF_SUPERVISE_STATE 指定。"
    exit 2
fi

# ---------------------------------------------------------------- the state folder and the one-instance lock

mkdir -p "$STATE/log" "$STATE/proc" 2>/dev/null && chmod 700 "$STATE" "$STATE/log" "$STATE/proc" 2>/dev/null
if [ ! -d "$STATE/log" ] || [ ! -w "$STATE" ] || [ ! -w "$STATE/log" ] || [ ! -w "$STATE/proc" ]; then
    err "狀態資料夾 $STATE 寫不進去，所以沒有啟動任何行程（沒有記錄就不跑）；請改它的權限，或用 ABF_SUPERVISE_STATE 指到寫得進的資料夾。"
    exit 2
fi
if ! exec 9>>"$STATE/supervise.lock"; then
    err "鎖檔 $STATE/supervise.lock 開不起來，所以沒有啟動任何行程；請檢查狀態資料夾的權限。"
    exit 2
fi
# up to 2 s: a --status probe holds the lock for a moment, and that is not "already running"
if ! flock -w 2 9; then
    say "已經有一份看守腳本在跑，這一份不再啟動任何東西；用 $SELF --status 看現況。"
    exit 0
fi
chmod 600 "$STATE/supervise.lock" 2>/dev/null
printf '%s\n' "$$" > "$STATE/supervise.pid"
rm -f "$STATE"/proc/* 2>/dev/null

SLOG="$STATE/supervise.log"
slog() { printf '%(%Y-%m-%d %H:%M:%S)T %s\n' -1 "$*" >> "$SLOG"; }

rotate_start() { # a file nobody is writing: move it aside when it is over the limit
    local f=$1 size
    [ -f "$f" ] || return 0
    size=$(stat -c %s "$f" 2>/dev/null || echo 0)
    [ "$size" -gt "$LOGMAX" ] && mv -f "$f" "$f.1"
    return 0
}
rotate_live() { # a file that is being appended to: copy, then empty it (the writer keeps going); 0 = it was rotated
    local f=$1 size
    [ -f "$f" ] || return 1
    size=$(stat -c %s "$f" 2>/dev/null || echo 0)
    [ "$size" -gt "$LOGMAX" ] || return 1
    if cp -f "$f" "$f.1" 2>/dev/null; then
        : > "$f"
    else
        : > "$f"   # empty it anyway: a log that cannot be rotated must still not grow without end
        slog "換檔失敗：${f##*/} 複製不了舊的一份，舊內容已丟棄，記錄才不會無限長；請檢查 ${f%/*} 的權限與空間"
        return 2
    fi
    return 0
}

rotate_start "$SLOG"
for n in "${NAMES[@]}"; do rotate_start "$STATE/log/$n.log"; done
slog "看守腳本啟動 pid=$$，看守 ${#NAMES[@]} 個行程"

# the start-up message goes out before any process starts; a closed stdout (| true) must not kill us
trap '' PIPE
say "看守腳本已啟動，正在看守 ${#NAMES[@]} 個行程；用 $SELF --status 看現況，停止用 $SELF --stop、Ctrl-C 或 kill（SIGTERM）。"
trap - PIPE

# ---------------------------------------------------------------- one runner per process

sup_alive() { pid_alive "$SUPPID"; }

runner() { # name command takeover(0|1)
    local name=$1 cmd=$2 takeover=${3:-0} pid="" cur="" sp="" stopping=0 n=0 fails=0 restarts=0 wd w i t0 t1 lived rc="" first=1 run
    local lg="$STATE/log/$name.log" pf="$STATE/proc/$name" started_text="-"
    exec 2>/dev/null
    set -m
    on_term() {
        stopping=1
        [ -n "$cur" ] && kill -TERM -- "-$cur" 2>/dev/null
        [ -n "$sp" ] && kill "$sp" 2>/dev/null
        return 0
    }
    trap on_term TERM INT HUP

    write_state() { # running(0|1)
        printf 'pid=%s\nstarted=%s\nrestarts=%s\nrunning=%s\nlast_rc=%s\nfails=%s\n' \
            "$pid" "$started_text" "$restarts" "$1" "${rc:-}" "$fails" > "$pf.tmp" && mv -f "$pf.tmp" "$pf"
    }

    if [ "$takeover" -eq 1 ]; then
        # a runner of this name died: carry its counts on, and stop what it left running so there is one copy
        local k v op="" orun=0 l
        local -a f
        while IFS='=' read -r k v; do
            case $k in pid) op=$v ;; running) orun=$v ;; restarts) restarts=$v ;; fails) fails=$v ;; esac
        done < "$pf" 2>/dev/null
        [[ $restarts =~ ^[0-9]+$ ]] || restarts=0
        [[ $fails =~ ^[0-9]+$ ]] || fails=0
        first=0; restarts=$((restarts + 1))
        if [ "$orun" = 1 ] && [[ $op =~ ^[0-9]+$ ]] && pid_alive "$op" && read -r l < "/proc/$op/stat" 2>/dev/null; then
            read -r -a f <<<"${l##*) }"
            if [ "${f[2]:-}" = "$op" ]; then
                slog "$name 接手：舊的行程 $op 還在跑，先把它停掉，免得出現兩份"
                kill -TERM -- "-$op" 2>/dev/null
                now_us; k=$(( NOW + WAIT_US ))
                while pid_alive "$op" && { now_us; [ "$NOW" -lt "$k" ]; }; do sleep 0.1; done
                pid_alive "$op" && kill -KILL -- "-$op" 2>/dev/null
            fi
        fi
        pid=""
    fi

    # a leading VAR=value is not a program: the line then runs through env(1)
    if [[ $cmd =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then run="exec /usr/bin/env $cmd"; else run="exec $cmd"; fi

    while [ "$stopping" -eq 0 ]; do
        if ! sup_alive; then slog "$name 看守腳本本體已不在，這個看守子殼不再重啟行程，結束"; break; fi
        rotate_start "$lg"
        ( cd "$HOME" 2>/dev/null; umask "$ORIG_UMASK"; exec bash -l -c "$run" ) >>"$lg" 2>&1 </dev/null 9>&- &
        pid=$!; cur=$pid
        # a stop signal that landed before cur was set had nobody to pass it to
        [ "$stopping" -eq 1 ] && kill -TERM -- "-$cur" 2>/dev/null
        printf -v started_text '%(%Y-%m-%d %H:%M:%S)T' -1
        now_us; t0=$NOW
        write_state 1
        if [ "$first" -eq 1 ]; then slog "$name 啟動 pid=$pid"; first=0
        else slog "$name 重啟 #$restarts pid=$pid"; fi
        wait "$pid"; rc=$?
        if [ "$stopping" -eq 1 ]; then
            # the stop signal was already passed to the group; give it WAIT, then SIGKILL
            ( now_us; end=$(( NOW + WAIT_US )); while now_us; [ "$NOW" -lt "$end" ]; do sleep 0.1; done
              kill -KILL -- "-$pid" ) >/dev/null 2>&1 9>&- &
            wd=$!
            while kill -0 "$pid" 2>/dev/null; do wait "$pid"; rc=$?; done
            while kill -0 -- "-$pid" 2>/dev/null; do sleep 0.1; done
            kill "$wd" 2>/dev/null; wait "$wd" 2>/dev/null
            slog "$name 已停止（結束碼 $rc）"
            break
        fi
        cur=""
        now_us; t1=$NOW; lived=$(( t1 - t0 )); [ "$lived" -lt 0 ] && lived=0
        slog "$name 結束碼 $rc（存活 $(fmt_us "$lived") 秒）"
        case $rc in 126|127) slog "$name 無法啟動：執行檔找不到或不能執行（結束碼 $rc），會照間隔再試" ;; esac
        if [ "$lived" -ge "$STABLE_US" ]; then n=0; fails=0; else fails=$((fails + 1)); fi
        if [ "$fails" -ge 5 ] && [ $(( fails % 5 )) -eq 0 ]; then
            slog "警告 $name 連續失敗 $fails 次（每次都活不到 $(fmt_us "$STABLE_US") 秒），可能出了問題，請看 log/$name.log"
        fi
        w=$BASE_US; i=0
        while [ "$i" -lt "$n" ] && [ "$w" -lt "$MAX_US" ]; do w=$(( w * 2 )); i=$((i + 1)); done
        [ "$w" -gt "$MAX_US" ] && w=$MAX_US
        [ "$n" -lt 40 ] && n=$((n + 1))
        restarts=$((restarts + 1))
        write_state 0
        [ "$stopping" -eq 1 ] && break
        slog "$name 下次間隔 $(fmt_us "$w") 秒，之後重啟"
        sleep "$(fmt_us "$w")" 9>&- & sp=$!
        [ "$stopping" -eq 1 ] && kill "$sp" 2>/dev/null
        wait "$sp"
        kill "$sp" 2>/dev/null; wait "$sp" 2>/dev/null; sp=""
    done
    write_state 0
    exit 0
}

RPIDS=(); stopping=0; hup=0; msp=""; GPID=""
start_guardian() {
    # One guardian for all runners. When this script is gone (kill -9) it tells the runners to stop their
    # processes and end, so nothing keeps restarting and no second set can start next to the first one.
    # It holds no lock, and a pid is signalled only if it still looks like one of ours.
    local -a snap=("${RPIDS[@]}")
    if [ -n "$GPID" ]; then kill "$GPID" 2>/dev/null; wait "$GPID" 2>/dev/null; fi
    ( gsp=""; p=""
      trap 'kill "$gsp" 2>/dev/null; exit 0' TERM
      while sup_alive; do sleep 0.5 & gsp=$!; wait "$gsp"; done
      for p in "${snap[@]}"; do
          grep -qa 'abf-supervise' "/proc/$p/cmdline" 2>/dev/null && kill -TERM "$p" 2>/dev/null
      done
      exit 0 ) 9>&- &
    GPID=$!
}
on_stop() {
    stopping=1
    local p
    for p in "${RPIDS[@]}"; do kill -TERM "$p" 2>/dev/null; done
    [ -n "$msp" ] && kill "$msp" 2>/dev/null
    return 0
}
on_hup() { hup=1; on_stop; }
trap on_stop TERM INT
trap on_hup HUP

for i in "${!NAMES[@]}"; do
    runner "${NAMES[$i]}" "${CMDS[$i]}" 0 &
    RPIDS+=($!)
done
[ "$stopping" -eq 1 ] && on_stop
start_guardian

while [ "$stopping" -eq 0 ]; do
    # a runner that died on its own is replaced; its process is stopped first so there is only one copy
    for i in "${!RPIDS[@]}"; do
        pid_alive "${RPIDS[$i]}" && continue
        wait "${RPIDS[$i]}" 2>/dev/null; rrc=$?
        [ "$stopping" -eq 1 ] && break
        slog "${NAMES[$i]} 的看守子殼不見了（結束碼 $rrc），本體重新接手看守"
        runner "${NAMES[$i]}" "${CMDS[$i]}" 1 &
        RPIDS[$i]=$!
        start_guardian
    done
    [ "$stopping" -eq 1 ] && break
    sleep "$(fmt_us "$TICK_US")" 9>&- & msp=$!
    [ "$stopping" -eq 1 ] && kill "$msp" 2>/dev/null
    wait "$msp" 2>/dev/null
    kill "$msp" 2>/dev/null; wait "$msp" 2>/dev/null; msp=""
    [ "$stopping" -eq 1 ] && break
    for n in "${NAMES[@]}"; do rotate_live "$STATE/log/$n.log"; done
    rotate_live "$SLOG"; [ $? -eq 0 ] && slog "supervise.log 已換檔，舊的一份在 supervise.log.1"
done

for p in "${RPIDS[@]}"; do
    while kill -0 "$p" 2>/dev/null; do wait "$p" 2>/dev/null; done
done
if [ -n "$GPID" ]; then kill "$GPID" 2>/dev/null; wait "$GPID" 2>/dev/null; fi
slog "看守腳本已停止"
[ "$hup" -eq 1 ] && exit 129
exit 0
