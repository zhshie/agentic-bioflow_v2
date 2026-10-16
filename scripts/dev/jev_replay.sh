#!/bin/bash
# Nothing existing: replaying a labelled question bank through one script and scoring the answers is this project's own acceptance step for the Jev triage; no maintained tool knows our labels or our jev.sh contract.
#
# Maintainer's manual acceptance for feature 015 (docs/TESTING.md, Half 2).
# Runs the approved question bank (specs/015-jev-triage/labels.json, 42 items)
# through scripts/jev.sh, scores the items that would actually reach Jev (37 of
# them: the ones the runs skill hands to its earlier rules - exit code 137 and a
# site refusal line - are left out and shown to be left out), and prints the
# report: accuracy overall and per category, the wrong ids, a threshold
# suggestion, the characters the AI would read with and without Jev, an
# estimate of tokens, and latency. A real run also writes it to
# specs/015-jev-triage/replay-report.md.
#
#   TYPESAFE_API_KEY=... scripts/dev/jev_replay.sh [--report <file>]
#   JEV_DRY_RUN=<dir> TYPESAFE_API_KEY=any scripts/dev/jev_replay.sh   # offline; writes no report file unless --report
#
# Refuses without a key. Not in tests/run_all.sh (it needs the real service);
# tests/jev_test.sh runs it offline against fixtures. "Recommended to switch
# on" is written only for a REAL run at 34/37 (90%) or better, and docs/SETTINGS.md
# says it only after the maintainer has seen such a report.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
JEV="$ROOT/scripts/jev.sh"
LABELS="${JEV_LABELS:-$ROOT/specs/015-jev-triage/labels.json}"
REPORT_FILE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --report) REPORT_FILE="${2-}"; shift 2 ;;
        *) echo "usage: jev_replay.sh [--report <file>]" >&2; exit 2 ;;
    esac
done

. "$ROOT/scripts/settings.sh" || exit 1
command -v jq >/dev/null 2>&1 || { echo "jev_replay.sh needs jq" >&2; exit 1; }
if [ -z "${TYPESAFE_API_KEY:-}" ] && [ ! -r "$(jev_key_file)" ]; then
    echo "jev_replay.sh needs a TypeSafe key: set TYPESAFE_API_KEY (or create the key file, docs/SETTINGS.md)." >&2
    echo "With JEV_DRY_RUN=<dir> the key can be any placeholder; nothing is sent." >&2
    exit 1
fi
[ -r "$LABELS" ] || { echo "no question bank at $LABELS" >&2; exit 1; }

work="$(mktemp -d "${TMPDIR:-/tmp}/jev-replay.XXXXXX")" || exit 1
trap 'rm -rf "$work"' EXIT
export JEV_ENABLED=true
export JEV_DAILY_CAP="${JEV_DAILY_CAP:-1000}"
DRY=0
if [ -n "${JEV_DRY_RUN:-}" ]; then
    DRY=1; export AGENTIC_BIOFLOW_STATE_DIR="$work/state"   # an offline rehearsal must not touch the real counter
fi
min_conf="$(jev_setting min_confidence)"

now_ms() { local n; n="$(date +%s%N 2>/dev/null)"; case "$n" in *N*|'') echo $(( $(date +%s) * 1000 )) ;; *) echo $(( n / 1000000 )) ;; esac; }

results="$work/results.tsv"; skipped="$work/skipped.txt"; : > "$results"; : > "$skipped"
while IFS=$'\t' read -r id code label; do
    f="$work/err.$id"
    jq -r --arg id "$id" '.[]|select(.id==$id)|.err_tail' "$LABELS" > "$f"
    if [ "$code" = 137 ] || grep -q 'DENY-DOMAIN' "$f"; then
        why="exit 137"; [ "$code" = 137 ] || why="site refusal line"
        printf '%s\t%s\n' "$id" "$why" >> "$skipped"
        continue
    fi
    ex="$code"; [ "$code" = null ] && ex=none
    without="$(jq -Rs 'length' < "$f")"
    with200="$(tail -n 200 "$f" | jq -Rs 'length')"
    t0="$(now_ms)"
    out="$("$JEV" triage --err "$f" --exit "$ex" 2>/dev/null)"
    t1="$(now_ms)"
    m="$(grep -m1 '^JEV status=' <<<"$out")"
    status="$(sed -n 's/^JEV status=\([a-z_]*\) .*/\1/p' <<<"$m")"
    cat_="$(sed -n 's/.* category=\([a-z_-]*\) .*/\1/p' <<<"$m")"
    conf="$(sed -n 's/.* confidence=\([0-9.-]*\) .*/\1/p' <<<"$m")"
    # what the AI reads: the last 200 lines when Jev was sure, the whole file otherwise
    with="$without"
    if [ "$status" = ok ] && [ "$cat_" != unknown ] && awk -v c="$conf" -v m="$min_conf" 'BEGIN{exit !(c+0>=m+0)}'; then with="$with200"; fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$id" "$label" "${status:-none}" "${cat_:--}" "${conf:--}" "$with" "$without" "$((t1 - t0))" "$with200" >> "$results"
done < <(jq -r '.[]|[.id, (.exit_code|tostring), .label]|@tsv' "$LABELS")

report="$work/report.md"
{
    echo "# Jev 回放報告（feature 015）"
    echo
    if [ "$DRY" = 1 ]; then echo "> 離線演練（JEV_DRY_RUN）：用的是假回應，這份數字不代表 Jev 的準度。"; echo; fi
    awk -F'\t' -v dry="$DRY" '
        { n++; if ($3=="ok" && $4==$2) ok++; else { wrong = wrong " " $1 }
          tot[$2]++; if ($3=="ok" && $4==$2) hit[$2]++
          w += $6; wo += $7; ms += $8; chars += $9
          conf[n] = $5; good[n] = ($3=="ok" && $4==$2) }
        END {
            pct = (n ? 100 * ok / n : 0)
            printf "## 結果\n\n- 答對率：%d/%d（%.1f%%）\n", ok, n, pct
            if (dry == 0 && n > 0 && ok * 10 >= n * 9) printf "- 結論：達到 90%%，%s。\n", "建議" "開啟"
            else if (dry == 0) printf "- 結論：未達 90%%，文件不寫建議用語。\n"
            printf "- 答錯題號：%s\n", (wrong == "" ? "無" : substr(wrong, 2))
            printf "\n## 各類答對率\n\n| 類別 | 答對/題數 |\n|---|---|\n"
            for (c in tot) printf "| %s | %d/%d |\n", c, hit[c]+0, tot[c]
            # smallest threshold whose confident answers are right at least 90% of the time
            rec = "none"
            for (i = 0; i < 10 && rec == "none"; i++) {
                t = 0.50 + i * 0.05; a = 0; b = 0
                for (k = 1; k <= n; k++) if (conf[k] != "-" && conf[k] + 0 >= t) { a++; if (good[k]) b++ }
                if (a > 0 && b * 10 >= a * 9) rec = sprintf("%.2f", t)
            }
            printf "\n## 信心門檻建議\n\n- 建議的 jev.min_confidence：%s（預設 0.80；\"none\" 表示找不到達 90%% 的門檻）\n", rec
            printf "\n## 用量\n\n- 總延遲：%d ms（平均 %d ms／題）\n- 送出字數合計：%d（約 %d tokens，以 4 字元 ≈ 1 token 粗估；服務沒有回報實際 token）\n", ms, (n ? ms / n : 0), chars, chars / 4
        }' "$results"
    echo
    echo "## 錯誤訊息讀取量：有 Jev 與沒有 Jev"
    echo
    echo "高信心時 AI 只讀最後 200 行；其他情況照原流程讀整份。字數由題庫實際算出。"
    echo
    echo "| 題號 | 正確類別 | Jev 判斷 | 有 Jev 時 AI 讀的字數 | 沒有 Jev 時 AI 讀的字數 |"
    echo "|---|---|---|---|---|"
    awk -F'\t' '{ printf "| %s | %s | %s | %d | %d |\n", $1, $2, $4, $6, $7; w += $6; wo += $7 }
        END { printf "| 總計 | | | %d | %d |\n", w, wo }' "$results"
    echo
    echo "## 沒有呼叫 Jev 的題目"
    echo
    echo "這幾題被 runs 技能裡排在 Jev 之前的規則接走，不呼叫 Jev，也不計分："
    echo
    while IFS=$'\t' read -r id why; do echo "- $id（$why）：不呼叫 Jev"; done < "$skipped"
} > "$report"

cat "$report"
if [ -z "$REPORT_FILE" ] && [ "$DRY" = 0 ]; then REPORT_FILE="$ROOT/specs/015-jev-triage/replay-report.md"; fi
[ -n "$REPORT_FILE" ] && cp "$report" "$REPORT_FILE"
exit 0
