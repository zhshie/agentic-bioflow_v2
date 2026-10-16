#!/bin/bash
# Nothing existing: no maintained tool sorts a Nextflow task's stderr into fix routes; this is the thin client for the one API call (TypeSafe "Jev", a cloud classifier) that does.
#
# Optional step of the runs skill's FAILED flow (feature 015, docs/adr/0007).
# Off by default. The person brings their own TypeSafe key, turns it on, and is
# told once what leaves the machine. When it is off, keyless, capped or the
# service is down, this prints one machine line (and, except when off, one
# sentence saying so) and the skill carries on exactly as it did without Jev -
# never silently permissive (constitution VI-13).
#
#   jev.sh triage --err <.command.err> --exit <code|none>
#
# Always exits 0. Output:
#   line 1  JEV status=<ok|disabled|no_key|failed|capped|empty> category=<key|-> confidence=<0.00|-> sent_chars=<n>
#           (for the skill to parse; the skill never shows it to the user)
#   line 2  one sentence for the person ("Jev 判斷：container（信心 0.93）"); none when disabled.
# On the first real use on a machine a notice about what is sent comes before line 1.
#
# It only prints. It runs nothing from a response, starts or cancels nothing,
# deletes nothing but its own old day counters, and decides nothing that needs
# the user's consent: the category is a hint about which page of the runs skill
# to read first.
#
# Settings (scripts/settings.sh): jev.enabled (default false), jev.daily_cap (500),
# jev.min_confidence (0.80, read by the skill). Key: TYPESAFE_API_KEY, else the
# file beside the settings file (settings.sh jev_key_file), which the person
# creates mode 600; it is passed to curl on stdin (--config -), never on the
# command line, and never printed.
# JEV_ENDPOINT overrides the service URL (a future local service); JEV_DRY_RUN=<dir>
# reads fixture responses instead of calling the network (tests/fixtures/jev).
# State (not run state): $AGENTIC_BIOFLOW_STATE_DIR or
# ${XDG_STATE_HOME:-~/.local/state}/agentic-bioflow : jev-count-<day> (one
# integer) and jev-notice-shown (empty).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh" || { echo "JEV status=failed category=- confidence=- sent_chars=0"; echo "Jev 未回應，改用原流程（原因：找不到 settings.sh）"; exit 0; }

CATEGORIES="memory walltime network container input params tool_bug unknown"
ENDPOINT="${JEV_ENDPOINT:-https://api.typesafe.ai/v1/systemone}"
STATE_DIR="${AGENTIC_BIOFLOW_STATE_DIR:-${XDG_STATE_HOME:-${HOME:-}/.local/state}/agentic-bioflow}"
TODAY="${JEV_TODAY:-$(date +%F)}"

finish() {   # finish <status> <category> <confidence> <sent_chars> [sentence]
    printf 'JEV status=%s category=%s confidence=%s sent_chars=%s\n' "$1" "$2" "$3" "$4"
    [ -n "${5:-}" ] && printf '%s\n' "$5"
    exit 0
}
fail() {   # fail <reason>
    finish failed - - "${SENT:-0}" "Jev 未回應，改用原流程（原因：$1）"
}

[ "${1:-}" = triage ] || { echo "usage: jev.sh triage --err <file> --exit <code|none>" >&2; exit 2; }
shift
ERR_FILE=""; EXIT_CODE=none
while [ $# -gt 0 ]; do
    case "$1" in
        --err)  ERR_FILE="${2-}"; shift 2 ;;
        --exit) EXIT_CODE="${2-}"; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
SENT=0

# 1. off by default - the only thing an unconfigured deployment ever sees is the machine line
case "$(jev_setting enabled | tr 'A-Z' 'a-z')" in
    true|yes|on|1) ;;
    *) finish disabled - - 0 ;;
esac

# 2. tools
command -v curl >/dev/null 2>&1 || fail "這台機器找不到 curl"
command -v jq   >/dev/null 2>&1 || fail "這台機器找不到 jq"

work="$(mktemp -d "${TMPDIR:-/tmp}/jev.XXXXXX")" || fail "無法建立暫存目錄"
trap 'rm -rf "$work"' EXIT

# 3. the last 200 lines, as valid UTF-8
tailf="$work/tail"
if [ -n "$ERR_FILE" ] && [ -r "$ERR_FILE" ]; then
    tail -n 200 "$ERR_FILE" | tr -d '\000' > "$work/tail.raw"
    if command -v iconv >/dev/null 2>&1; then iconv -c -f UTF-8 -t UTF-8 < "$work/tail.raw" > "$tailf" 2>/dev/null || cp "$work/tail.raw" "$tailf"
    else cp "$work/tail.raw" "$tailf"; fi
else
    : > "$tailf"
fi
if ! grep -q '[^[:space:]]' "$tailf"; then
    finish empty unknown - 0 "Jev 沒有可判斷的內容（.command.err 是空的或讀不到），照原流程。"
fi
SENT="$(jq -Rs 'length' < "$tailf")"

# 4. the key: environment first, then the file beside the settings file
JEV_KEY="${TYPESAFE_API_KEY:-}"
if [ -z "$JEV_KEY" ]; then
    kf="$(jev_key_file)"
    if [ -r "$kf" ]; then
        priv="$(file_privacy "$kf")"
        if [ "${priv%% *}" = exposed ]; then
            case "$priv" in *"mode 400,"*) ;; *)
                finish no_key - - 0 "Jev 金鑰檔權限過寬（${priv#* }），請改成只有自己能讀（chmod 600）；這次先改用原流程。" ;;
            esac
        fi
        JEV_KEY="$(tr -d '\r\n' < "$kf")"
    fi
fi
[ -n "$JEV_KEY" ] || finish no_key - - 0 "Jev 已開啟但找不到金鑰，改用原流程（金鑰放法見 docs/SETTINGS.md）。"
JEV_KEY="${JEV_KEY//\"/}"; JEV_KEY="${JEV_KEY//\\/}"

# 5. daily cap (counted once per triage call, whatever happens to it)
cap="$(jev_setting daily_cap)"; case "$cap" in ''|*[!0-9]*) cap=500 ;; esac
count_file="$STATE_DIR/jev-count-$TODAY"
used=0; [ -r "$count_file" ] && used="$(tr -dc '0-9' < "$count_file")"; used="${used:-0}"
if [ "$used" -ge "$cap" ]; then
    finish capped - - 0 "今天的 Jev 次數已用完，改用原流程。"
fi

# 6. say once what is sent, before sending anything
mkdir -p "$STATE_DIR" 2>/dev/null
if [ ! -e "$STATE_DIR/jev-notice-shown" ]; then
    cat <<'NOTICE'
Jev 分診已開啟，這台機器第一次使用，先告知會送出什麼：
- 送出：失敗 task 的 .command.err 最後 200 行，加上 exit code，送到 api.typesafe.ai（可用 JEV_ENDPOINT 改指別處）。
- 內容可能含路徑與樣本名稱。TypeSafe 只對企業客戶提供「不保留資料」，一般金鑰不適用。
- 想關閉：把設定裡的 jev.enabled 改成 false，或刪掉那一行。
- 金鑰用你自備的，不會被印出，也不會寫進任何檔案。
NOTICE
    : > "$STATE_DIR/jev-notice-shown"
fi
find "$STATE_DIR" -maxdepth 1 -name 'jev-count-*' ! -name "jev-count-$TODAY" -exec rm -f {} + 2>/dev/null
echo $((used + 1)) > "$count_file"

# 7. the request
case "$EXIT_CODE" in ''|*[!0-9]*) exit_json=null ;; *) exit_json="$EXIT_CODE" ;; esac
req="$work/request.json"
jq -n --rawfile err "$tailf" --argjson code "$exit_json" '{
    model: "jev-latest",
    state: { exit_code: $code, err_tail: $err },
    questions: { category: {
        type: "choice",
        instructions: "The state is the last lines of stderr from one failed Nextflow task on an HPC cluster. Choose the single category that names the most likely cause.",
        criteria: {
            memory:    "the task ran out of memory (killed, out-of-memory, heap space, bad_alloc)",
            walltime:  "the task ran out of its time allowance (time limit, cancelled due to time)",
            network:   "the task could not reach a host outside the cluster (connection refused or timed out, could not resolve host, download failed)",
            container: "the container image could not be pulled, found, converted or started",
            input:     "an input file or samplesheet is missing, empty, truncated, malformed or the wrong format",
            params:    "a pipeline or tool option is invalid, missing or contradictory",
            tool_bug:  "the tool itself crashed (segmentation fault, stack trace, assertion) with valid inputs and options",
            unknown:   "none of the above fits, or the text is not enough to tell"
        }
    } }
}' > "$req" || fail "無法組出請求"

# 8. ask (fixture or network)
body=""
if [ -n "${JEV_DRY_RUN:-}" ]; then
    sum="$( { sha256sum "$tailf" 2>/dev/null || shasum -a 256 "$tailf"; } | cut -c1-64)"
    fx="$JEV_DRY_RUN/$sum.json"; [ -r "$fx" ] || fx="$JEV_DRY_RUN/default.json"
    [ -r "$fx" ] || fail "沒有對應的 fixture"
    first="$(head -n 1 "$fx" | tr -d '\r')"
    case "$first" in
        __timeout__)       fail "timeout" ;;
        __429_then_ok__)   body="$(tail -n +2 "$fx")" ;;
        __[0-9][0-9][0-9]__) fail "HTTP ${first//_/}" ;;
        *)                 body="$(cat "$fx")" ;;
    esac
else
    cfg="header = \"Authorization: Bearer $JEV_KEY\""
    resp="$work/response.json"
    for attempt in 1 2 3; do
        rc=0
        code="$(printf '%s\n' "$cfg" | curl -sS --max-time 10 -o "$resp" -w '%{http_code}' --config - \
                  -X POST -H 'Content-Type: application/json' --data-binary "@$req" "$ENDPOINT" 2>/dev/null)" || rc=$?
        if [ "$rc" -eq 28 ]; then fail "timeout"; fi
        if [ "$rc" -ne 0 ]; then fail "連線失敗（curl 代碼 $rc）"; fi
        case "$code" in
            200) body="$(cat "$resp")"; break ;;
            429|529)
                if [ "$attempt" -ge 3 ]; then fail "HTTP $code，重試後仍失敗"; fi
                if [ "$attempt" -eq 1 ]; then sleep 1; else sleep 3; fi
                ;;
            *) fail "HTTP ${code:-?}" ;;
        esac
    done
fi

# 9. read the answer; anything unexpected is a failure, never a guess
parsed="$(printf '%s' "$body" | jq -r 'select((.answers.category.choice|type)=="string" and (.answers.category.confidence|type)=="number") | "\(.answers.category.choice) \(.answers.category.confidence)"' 2>/dev/null)" \
    || fail "回應不是合法的 JSON"
[ -n "$parsed" ] || fail "回應格式不對（缺少 answers.category）"
choice="${parsed%% *}"; conf="${parsed##* }"
case " $CATEGORIES " in *" $choice "*) ;; *) fail "回應的類別不在清單內" ;; esac
awk -v c="$conf" 'BEGIN{exit !(c+0>=0 && c+0<=1)}' || fail "回應的信心不在 0 到 1 之間"
conf="$(LC_ALL=C awk -v c="$conf" 'BEGIN{printf "%.2f", c}')"

finish ok "$choice" "$conf" "$SENT" "Jev 判斷：$choice（信心 $conf）"
