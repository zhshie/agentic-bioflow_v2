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
#
# List file: ~/.config/abf-platform/processes (see deploy/wsl/processes.example). One process per
# line, "<name> <full command>"; "#" lines and blank lines are skipped; a name uses [a-z0-9-] and
# is unique. The command runs as `bash -c "exec <command>"`. Use absolute paths: a login task's
# PATH is short. The file must be owner-only (chmod 600). A token never goes in it: use
# --token-file. A line that looks like a token or a key (an "abf_" string of 20 or more letters
# and digits, an HTTP bearer prefix, or a private-key header) refuses the start.
#
# Exit codes: 0 ok (also "another supervisor is already running"); 1 --status and not running;
# 2 refused (bad list, bad rights, a token in the list, a missing tool, a folder that cannot be
# written).
#
# Knobs (environment variables; the defaults are the real ones, the others exist for tests):
#   ABF_SUPERVISE_STATE   state folder       ~/.local/state/abf-platform
#   ABF_SUPERVISE_BASE    first interval, s  2        (doubles after each quick failure)
#   ABF_SUPERVISE_MAX     longest interval   60
#   ABF_SUPERVISE_STABLE  alive this long = healthy, the interval starts over   30
#   ABF_SUPERVISE_WAIT    on stop, wait this long for a child before SIGKILL    10
#   ABF_SUPERVISE_LOGMAX  rotate a log above this many bytes   10485760  (10 MB)
#   ABF_SUPERVISE_TICK    how often the logs are checked while running, s       5
# Numbers may have decimals (0.2).
#
# State folder (folder 0700, files 0600): supervise.lock, supervise.pid, supervise.log (the
# supervisor's own events, each line timestamped), log/<name>.log (a process's output; the
# last rotated one is <name>.log.1), proc/<name> (name, pid, times, count - nothing else).
# The supervisor never reads a run's state and never prints the environment.
#
# Stop it with SIGTERM or Ctrl-C (it passes the signal on, waits, then SIGKILLs what is left).
# Do not kill -9 it: its children would live on and a second copy would start another set.

set -u
umask 077

SELF=$0
LIST_DEFAULT="${HOME:-}/.config/abf-platform/processes"
STATE="${ABF_SUPERVISE_STATE:-${HOME:-}/.local/state/abf-platform}"

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
fmt_us() { # 400000 -> 0.4 ; 2000000 -> 2
    local us=$1 i f
    i=$(( us / 1000000 )); f=$(printf '%06d' $(( us % 1000000 )))
    while [[ $f == *0 ]]; do f=${f%0}; done
    if [ -n "$f" ]; then printf '%s.%s\n' "$i" "$f"; else printf '%s\n' "$i"; fi
}

[ -n "${HOME:-}" ] || { err "環境裡沒有 HOME，看守腳本不知道清單與記錄放哪；請從登入後的終端執行，或設好 HOME 再試。"; exit 2; }

MODE=run
LIST=""
while [ $# -gt 0 ]; do
    case $1 in
        --list) [ $# -ge 2 ] || { err "--list 後面要接清單檔的路徑；例如 --list <清單檔>。"; exit 2; }; LIST=$2; shift 2 ;;
        --check) MODE=check; shift ;;
        --status) MODE=status; shift ;;
        -h|--help) sed -n '2,38p' "$SELF" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) err "不認得的選項「$1」；可用 --list、--check、--status，說明用 --help。"; exit 2 ;;
    esac
done
[ -n "$LIST" ] || LIST=$LIST_DEFAULT

for knob in BASE MAX STABLE WAIT; do
    eval "raw=\${ABF_SUPERVISE_$knob:-}"
    if [ -n "$raw" ] && ! to_us "$raw" >/dev/null; then
        err "環境變數 ABF_SUPERVISE_$knob 要是不帶單位的數字（例如 2 或 0.5）；請改正或清掉它。"; exit 2
    fi
done
BASE_US=$(to_us "${ABF_SUPERVISE_BASE:-2}")
MAX_US=$(to_us "${ABF_SUPERVISE_MAX:-60}")
STABLE_US=$(to_us "${ABF_SUPERVISE_STABLE:-30}")
WAIT_US=$(to_us "${ABF_SUPERVISE_WAIT:-10}")
TICK_US=$(to_us "${ABF_SUPERVISE_TICK:-5}") || TICK_US=5000000
LOGMAX=${ABF_SUPERVISE_LOGMAX:-10485760}
[[ $LOGMAX =~ ^[0-9]+$ ]] || { err "環境變數 ABF_SUPERVISE_LOGMAX 要是位元組數（整數）；請改正或清掉它。"; exit 2; }
[ "$MAX_US" -ge "$BASE_US" ] || MAX_US=$BASE_US

need_flock() {
    command -v flock >/dev/null 2>&1 || {
        err "這台機器缺 flock 這個工具，看守腳本沒有它就不能保證只跑一份；請先安裝（Ubuntu：apt install util-linux）再試。"
        exit 2
    }
}

# ---------------------------------------------------------------- the list

NAMES=(); CMDS=(); NERR=0
bad() { err "$*"; NERR=$((NERR + 1)); }

first_exe() { # command text -> its program word (quotes off, ~ and $HOME filled in)
    local -a w; local x
    read -r -a w <<<"$1"
    for x in "${w[@]}"; do
        [[ $x =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] && continue
        x=${x#[\"\']}; x=${x%[\"\']}
        case $x in
            '~/'*) x="$HOME/${x#'~/'}" ;;
            '$HOME/'*) x="$HOME/${x#'$HOME/'}" ;;
            '${HOME}/'*) x="$HOME/${x#'${HOME}/'}" ;;
        esac
        printf '%s\n' "$x"; return
    done
}

load_list() { # fills NAMES CMDS, counts problems in NERR, says each one with its line number
    local f=$1 mode ln=0 line name cmd i exe
    NAMES=(); CMDS=(); NERR=0
    local -a lnos=()
    if [ ! -f "$f" ] || [ ! -r "$f" ]; then
        bad "找不到或讀不到清單檔 $f；請照 deploy/wsl/processes.example 建一份（chmod 600），或用 --list 指定位置。"
        return
    fi
    mode=$(stat -c %a "$f" 2>/dev/null || echo 777)
    if [ $(( 8#$mode & 8#077 )) -ne 0 ]; then
        bad "清單檔 $f 的權限是 $mode，群組或其他人也能讀寫；它決定這個帳號會執行什麼，請先執行 chmod 600 $f。"
    fi
    while IFS= read -r line || [ -n "$line" ]; do
        ln=$((ln + 1))
        line=${line%$'\r'}
        # a token-shaped string is refused on every line, comments included
        if [[ $line =~ abf_[[:alnum:]]{20,} ]] || [[ $line == *'Bearer '* ]] || [[ $line == *'-----BEGIN'* ]]; then
            bad "清單檔第 $ln 行像是權杖或金鑰（這裡不回印內容）；清單不放權杖，請改用 --token-file 指向放權杖的檔案。"
            continue
        fi
        line=${line#"${line%%[![:space:]]*}"}
        case $line in ''|'#'*) continue ;; esac
        name=${line%%[[:space:]]*}
        cmd=${line#"$name"}
        cmd=${cmd#"${cmd%%[![:space:]]*}"}
        case $name in
            *[!abcdefghijklmnopqrstuvwxyz0123456789-]*)
                bad "清單檔第 $ln 行：名字「$name」不合法，名字只能用小寫英文字母、數字與減號；請改名。"; continue ;;
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
        exe=$(first_exe "$cmd")
        if [[ $exe == *'$'* ]]; then
            :   # a variable in the program word cannot be checked here
        elif [[ $exe == */* ]]; then
            if [ ! -e "$exe" ]; then
                bad "清單檔第 $ln 行（$name）：找不到執行檔 $exe；請確認路徑，或先安裝它。"
            elif [ ! -f "$exe" ] || [ ! -x "$exe" ]; then
                bad "清單檔第 $ln 行（$name）：$exe 不可執行；請執行 chmod +x $exe。"
            fi
        elif ! command -v "$exe" >/dev/null 2>&1; then
            bad "清單檔第 $ln 行（$name）：在 PATH 裡找不到執行檔「$exe」；請改成完整路徑（登入工作的 PATH 很短）。"
        fi
        NAMES+=("$name"); CMDS+=("$cmd"); lnos+=("$ln")
    done < "$f"
    if [ "$NERR" -eq 0 ] && [ "${#NAMES[@]}" -eq 0 ]; then
        bad "清單檔 $f 裡沒有可看守的行程（只有註解或空行）；請照 deploy/wsl/processes.example 加上要看守的行程。"
    fi
}

# ---------------------------------------------------------------- --status

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
    say "看守腳本在跑（行程編號 ${spid:-?}）。"
    shopt -s nullglob
    for pf in "$STATE"/proc/*; do
        [ -f "$pf" ] || continue
        pn=${pf##*/}; p_pid=""; p_start=""; p_n=0; p_run=0
        while IFS='=' read -r k v; do
            case $k in pid) p_pid=$v ;; started) p_start=$v ;; restarts) p_n=$v ;; running) p_run=$v ;; esac
        done < "$pf"
        if [ "$p_run" = 1 ] && [ -n "$p_pid" ] && kill -0 "$p_pid" 2>/dev/null; then
            say "$pn: 在跑  行程編號 $p_pid  上次啟動 $p_start  重啟次數 $p_n"
        else
            say "$pn: 沒在跑（等著重啟）  行程編號 -  上次啟動 ${p_start:--}  重啟次數 $p_n"
        fi
    done
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
if ! flock -n 9; then
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
rotate_live() { # a file that is being appended to: copy, then empty it (the writer keeps going)
    local f=$1 size
    [ -f "$f" ] || return 0
    size=$(stat -c %s "$f" 2>/dev/null || echo 0)
    if [ "$size" -gt "$LOGMAX" ]; then
        cp -f "$f" "$f.1" && : > "$f"
        return 0
    fi
    return 1
}

rotate_start "$SLOG"
for n in "${NAMES[@]}"; do rotate_start "$STATE/log/$n.log"; done
slog "看守腳本啟動 pid=$$，看守 ${#NAMES[@]} 個行程"

# ---------------------------------------------------------------- one runner per process

now_us() { NOW=${EPOCHREALTIME/[.,]/}; }

runner() { # name command
    local name=$1 cmd=$2 pid="" cur="" stopping=0 n=0 restarts=0 wd w i t0 t1 lived rc first=1 sp
    local lg="$STATE/log/$name.log" pf="$STATE/proc/$name"
    exec 9>&-
    exec 2>/dev/null
    set -m
    on_term() { stopping=1; [ -n "$cur" ] && kill -TERM -- "-$cur" 2>/dev/null; return 0; }
    trap on_term TERM INT HUP

    write_state() { # running(0|1)
        printf 'pid=%s\nstarted=%s\nrestarts=%s\nrunning=%s\nlast_rc=%s\n' \
            "$pid" "$started_text" "$restarts" "$1" "${rc:-}" > "$pf.tmp" && mv -f "$pf.tmp" "$pf"
    }
    local started_text="-"
    while [ "$stopping" -eq 0 ]; do
        rotate_start "$lg"
        bash -c "exec $cmd" >>"$lg" 2>&1 </dev/null &
        pid=$!; cur=$pid
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
        now_us; t1=$NOW; lived=$(( t1 - t0 ))
        slog "$name 結束碼 $rc（存活 $(fmt_us "$lived") 秒）"
        case $rc in 126|127) slog "$name 無法啟動：執行檔找不到或不能執行（結束碼 $rc），會照間隔再試" ;; esac
        [ "$lived" -ge "$STABLE_US" ] && n=0
        w=$BASE_US; i=0
        while [ "$i" -lt "$n" ] && [ "$w" -lt "$MAX_US" ]; do w=$(( w * 2 )); i=$((i + 1)); done
        [ "$w" -gt "$MAX_US" ] && w=$MAX_US
        [ "$n" -lt 40 ] && n=$((n + 1))
        restarts=$((restarts + 1))
        write_state 0
        slog "$name 下次間隔 $(fmt_us "$w") 秒，之後重啟"
        sleep "$(fmt_us "$w")" & sp=$!
        wait "$sp"
        kill "$sp" 2>/dev/null; wait "$sp" 2>/dev/null
    done
    write_state 0
    exit 0
}

RPIDS=(); stopping=0
for i in "${!NAMES[@]}"; do
    runner "${NAMES[$i]}" "${CMDS[$i]}" &
    RPIDS+=($!)
done

on_stop() {
    stopping=1
    local p
    for p in "${RPIDS[@]}"; do kill -TERM "$p" 2>/dev/null; done
    return 0
}
trap on_stop TERM INT HUP

say "看守腳本已啟動，正在看守 ${#NAMES[@]} 個行程；用 $SELF --status 看現況，停止用 Ctrl-C 或 kill（SIGTERM）。"

while [ "$stopping" -eq 0 ]; do
    alive=0
    for p in "${RPIDS[@]}"; do kill -0 "$p" 2>/dev/null && alive=$((alive + 1)); done
    if [ "$alive" -eq 0 ]; then slog "所有看守的行程都已離開，看守腳本結束"; exit 1; fi
    sleep "$(fmt_us "$TICK_US")" 9>&- & sp=$!
    wait "$sp" 2>/dev/null
    kill "$sp" 2>/dev/null; wait "$sp" 2>/dev/null
    [ "$stopping" -eq 1 ] && break
    for n in "${NAMES[@]}"; do rotate_live "$STATE/log/$n.log"; done
    rotate_live "$SLOG" && slog "supervise.log 已換檔，舊的一份在 supervise.log.1"
done

for p in "${RPIDS[@]}"; do
    while kill -0 "$p" 2>/dev/null; do wait "$p" 2>/dev/null; done
done
slog "看守腳本已停止"
exit 0
