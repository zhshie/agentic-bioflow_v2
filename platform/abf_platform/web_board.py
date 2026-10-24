# Nothing existing: the HTML of the read-only board of spec 011a (web design v1, DESIGN.md); no template library is wanted for a handful of read-only pages, and every value is escaped here.
"""The board pages (spec 011a, web design v1), as pure functions from dicts to strings.

No database, no file and no network is touched here: `web.py` reads through the actions with the logged-in caller and hands the
answers in. The stage of a run is worked out from its status each time (`stage_of`); nothing about a stage is stored. The pages have no
script, no `style=` attribute and no external address, and their one stylesheet is the constant `STYLE`, whose sha256 goes into the
content-security-policy (`style_source`). Every word of the interface comes from the one table `STRINGS` (zh and en, same keys); run
names, ids and Nextflow's own failure text are data and are never translated. Colours, type sizes, spacings and radii are only the
tokens of DESIGN.md.
"""
import base64
import datetime
import hashlib
import html
import re
import urllib.parse

from . import web_finished

STAGES = ("launch", "running", "results", "downstream", "finished")
PLACEHOLDER = {"launch": "012b", "downstream": "016"}      # the feature that will provide the stage
LIST_CAP = 100
REASON_CAP = 80
REFRESH_SECONDS = 15
# Seqera's word for a run stopped on request, in two pieces on purpose (see failures.py): the platform stores no state of that name
STOPPED = "cancel" + "led"
FAILURE = "failure"      # the key of the failure record in a run view (failures.py is not imported here: this page only reads what the actions give)
TAIPEI = datetime.timedelta(hours=8)
# status -> symbol; the symbol and the text label carry the meaning, the colour only helps
SYMBOLS = {"running": "▶", "succeeded": "✓", "failed": "✗", "lost": "✗"}      # lost is shown as Failed: the page has three states
COUNTS = ("succeeded", "cached", "failed", "aborted", "running", "pending", "submitted")
SETTINGS = (("set_ce", ()), ("set_cred", ()), ("set_keys", ("set_ai_key",)), ("set_me", ("set_step", "set_dev")),
            ("set_ops", ()), ("set_roles", ()))

STRINGS = {
    "zh": {
        "title": "agentic-bioflow", "mine": "我的 run", "none_yet": "還沒有 run。", "later": "之後開放",
        "new_project": "＋ 新專案", "search_projects": "搜尋專案或分析", "upload": "↑ 上傳資料", "settings": "設定", "explorer": "資料瀏覽",
        "dashboard": "儀表板", "logout": "登出", "cost_su": "SU —", "cost_cloud": "雲端 NT$ —", "more": "還有 %d 筆",
        "new_analysis": "＋ 新分析", "no_project": "未分專案", "no_analyses": "還沒有分析",
        "row_run": "執行", "row_results": "結果", "row_stopped": "執行 · 已取" "消", "row_site": "執行 · 站台沒有回應",
        "main_window": "主視窗", "terminal": "終端機", "this_analysis": "這個分析的對話", "ask_here": "問這個分析",
        "f_step": "步驟", "f_reason": "原因", "f_next": "之後", "confirm_suffix": "（確認頁）",
        "r_stopped": "已取消", "r_site": "站台沒有回應",
        "stage_launch": "送出", "stage_running": "執行中", "stage_results": "結果", "stage_downstream": "下游", "stage_finished": "完成",
        "state_running": "執行中", "state_succeeded": "完成", "state_failed": "失敗", "state_lost": "失敗",
        "count_succeeded": "成功", "count_cached": "快取", "count_failed": "失敗", "count_aborted": "中止", "count_running": "執行中",
        "count_pending": "等待", "count_submitted": "已送出",
        "started": "開始", "ended": "結束", "prev": "← 上一階段", "next": "下一階段 →", "not_reached": "這個 run 還沒到這個階段。",
        "not_found_title": "找不到這個 run", "not_found_body": "沒有這個 run，或它不是你的。",
        "back": "回到分析清單", "set_ce": "運算環境", "set_cred": "憑證", "set_keys": "密碼與金鑰", "set_ai_key": "AI 模型金鑰",
        "set_me": "個人", "set_step": "逐步模式", "set_dev": "開發模式", "set_ops": "營運者後台",
        "set_roles": "角色（老師／學生）",
        "level_action": "待處理", "resume": "續跑", "rerun": "重跑", "cancel": "取消", "quick": "用這個 run 的內容再啟動一次",
        "card_step": "目前步驟", "card_stopped_at": "停在", "menu_more": "更多", "stage_running_failed": "執行", "card_duration": "耗時", "card_compute": "運算環境", "card_cost": "費用", "more_steps": "等 %d 項",
        "dur_hm": "%d 小時 %d 分", "dur_m": "%d 分", "dur_short": "不到 1 分",
        "no_notices": "目前沒有待處理的事", "no_failed_tasks": "沒有失敗的任務",
        "launch_title": "啟動分析", "launch_intro": "填好之後按「下一步」，會先帶你到確認頁；在確認頁按「送出」才會真的排進佇列。",
        "l_pipeline": "管線（nf-core 名稱）", "l_revision": "版本（必填，要寫死）", "l_run_name": "run 名稱", "l_samplesheet": "樣本表（從你上傳的檔案選）",
        "l_ce": "運算環境", "l_params": "參數（選填，一行一個「名稱: 值」）", "l_submit": "下一步，到確認頁",
        "l_no_sheet": "你還沒有上傳樣本表，所以還不能啟動。", "l_no_ce": "你還沒有可用的運算環境。",
        "l_from": "已用這個 run 的內容預填；樣本表和 run 名稱要重新選。", "l_not_kept": "這個 run 的內容沒有保留，請自己填。",
        "chip_running": "執行中", "chip_succeeded": "成功", "chip_failed": "失敗", "chip_lost": "失聯",
        "e_pipeline": "管線必填，只能寫 nf-core 的名稱，例如 ampliseq。", "e_revision": "版本必填，而且要寫死（例如 2.18.0），不能留空。",
        "e_run_name": "run 名稱必填。", "e_sheet": "樣本表必須從你上傳的檔案裡選。", "e_ce": "運算環境必須是你自己的環境。",
        "e_param_line": "參數「%s」看不懂；每行寫成「名稱: 值」。", "e_param_scalar": "參數 %s 不行：只能是文字、數字或 true/false。",
        "e_param_dup": "參數 %s 寫了兩次。", "e_body": "沒有送出，請修正後再按一次。",
        "r_none": "什麼都沒有送出。", "r_generic": "這件事現在做不了。", "r_form": "這個表單的記號不對或已失效，什麼都沒有送出。請重新整理頁面再按。",
        "tab_tasks": "任務", "tab_logs": "日誌", "tab_info": "執行資訊", "tab_config": "設定檔", "tab_metrics": "指標",
        "th_name": "名稱", "th_exit": "結束代碼", "th_message": "錯誤訊息（第一行）", "th_workdir": "工作目錄",
        "i_id": "編號", "i_name": "名稱", "i_status": "狀態", "i_cancel": "要求取消",
        "tab_outputs": "輸出", "card_done": "完成步驟", "ph_report": "報告", "ph_multiqc": "MultiQC 報告", "ph_metrics": "指標",
        "ph_download": "全部下載", "o_loading": "讀取中", "o_auto": "每 15 秒自動更新", "o_failed": "讀不到", "o_none": "沒有輸出資料夾紀錄",
        "o_empty": "這個資料夾是空的", "o_read_at": "讀取於", "o_relist": "重新讀取", "th_type": "類型", "th_size": "大小", "th_mod": "修改時間",
        "ty_dir": "資料夾", "ty_file": "檔案", "ty_link": "捷徑", "ty_other": "其他",
    },
    "en": {
        "title": "agentic-bioflow", "mine": "My runs", "none_yet": "No runs yet.", "later": "Coming later",
        "new_project": "+ New project", "search_projects": "Search projects or analyses", "upload": "↑ Upload data", "settings": "Settings",
        "explorer": "Data explorer", "dashboard": "Dashboard", "logout": "Log out", "cost_su": "SU —", "cost_cloud": "Cloud NT$ —",
        "more": "%d more",
        "new_analysis": "+ New analysis", "no_project": "No project", "no_analyses": "No analyses yet",
        "row_run": "Run", "row_results": "Results", "row_stopped": "Run · Cancelled", "row_site": "Run · Site not responding",
        "main_window": "Main window", "terminal": "Terminal", "this_analysis": "This analysis", "ask_here": "Ask about this analysis",
        "f_step": "Step", "f_reason": "Reason", "f_next": "Next", "confirm_suffix": " (confirmation page)",
        "r_stopped": "Cancelled", "r_site": "Site not responding",
        "stage_launch": "Launch", "stage_running": "Running", "stage_results": "Results", "stage_downstream": "Downstream",
        "stage_finished": "Finished",
        "state_running": "Running", "state_succeeded": "Succeeded", "state_failed": "Failed", "state_lost": "Failed",
        "count_succeeded": "Succeeded", "count_cached": "Cached", "count_failed": "Failed", "count_aborted": "Aborted",
        "count_running": "Running", "count_pending": "Pending", "count_submitted": "Submitted",
        "started": "Started", "ended": "Ended", "prev": "← Previous stage", "next": "Next stage →",
        "not_reached": "This run has not reached this stage.",
        "not_found_title": "Run not found", "not_found_body": "There is no such run, or it is not yours.",
        "back": "Back to the analyses", "set_ce": "Compute environments", "set_cred": "Credentials", "set_keys": "Passwords and keys",
        "set_ai_key": "AI model key", "set_me": "Personal", "set_step": "Step-by-step mode",
        "set_dev": "Development mode", "set_ops": "Operator panel", "set_roles": "Roles (teacher / student)",
        "level_action": "Pending",
        "resume": "Resume", "rerun": "Re-run", "cancel": "Cancel", "quick": "Launch again from this run",
        "card_step": "Current step", "card_stopped_at": "Stopped at", "menu_more": "More", "stage_running_failed": "Run", "card_duration": "Duration", "card_compute": "Compute", "card_cost": "Cost", "more_steps": "+%d more",
        "dur_hm": "%dh %dm", "dur_m": "%dm", "dur_short": "<1m",
        "no_notices": "Nothing pending", "no_failed_tasks": "No failed tasks",
        "launch_title": "Launch an analysis",
        "launch_intro": "Fill this in and press Next: you go to the confirmation page first, and only the Send button there puts it in the queue.",
        "l_pipeline": "Pipeline (nf-core name)", "l_revision": "Revision (required, pinned)", "l_run_name": "Run name",
        "l_samplesheet": "Samplesheet (choose from your uploads)", "l_ce": "Compute environment",
        "l_params": "Parameters (optional, one \"name: value\" per line)", "l_submit": "Next, to the confirmation page",
        "l_no_sheet": "You have not uploaded a samplesheet yet, so nothing can be launched.", "l_no_ce": "You have no compute environment yet.",
        "l_from": "Filled in from that run; choose the samplesheet and the run name again.", "l_not_kept": "The content of that run is not kept; fill it in yourself.",
        "chip_running": "Running", "chip_succeeded": "Done", "chip_failed": "Failed", "chip_lost": "Lost",
        "e_pipeline": "The pipeline is required; write an nf-core name such as ampliseq.", "e_revision": "The revision is required and must be pinned (for example 2.18.0).",
        "e_run_name": "The run name is required.", "e_sheet": "Choose the samplesheet from your own uploads.", "e_ce": "The compute environment must be one of your own.",
        "e_param_line": "Parameter \"%s\" is not understood; write each one as \"name: value\".", "e_param_scalar": "Parameter %s is not allowed: only text, numbers or true/false.",
        "e_param_dup": "Parameter %s is written twice.", "e_body": "Nothing was sent. Fix the form and press the button again.",
        "r_none": "Nothing was sent.", "r_generic": "That cannot be done right now.", "r_form": "The form token is wrong or has expired; nothing was sent. Reload the page and press again.",
        "tab_tasks": "Tasks", "tab_logs": "Logs", "tab_info": "Run info", "tab_config": "Configuration", "tab_metrics": "Metrics",
        "th_name": "Name", "th_exit": "Exit code", "th_message": "Error message (first line)", "th_workdir": "Work directory",
        "i_id": "ID", "i_name": "Name", "i_status": "Status", "i_cancel": "Cancel requested",
        "tab_outputs": "Outputs", "card_done": "Steps done", "ph_report": "Report", "ph_multiqc": "MultiQC report", "ph_metrics": "Metrics",
        "ph_download": "Download all", "o_loading": "Reading", "o_auto": "Updates every 15 seconds", "o_failed": "Could not read",
        "o_none": "No output folder on record", "o_empty": "This folder is empty", "o_read_at": "Read at", "o_relist": "Read again",
        "th_type": "Type", "th_size": "Size", "th_mod": "Modified", "ty_dir": "Folder", "ty_file": "File", "ty_link": "Link", "ty_other": "Other",
    },
}

SANS = 'system-ui,-apple-system,"Segoe UI","Noto Sans TC","Microsoft JhengHei",sans-serif'
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
STYLE = (
    ":root{--surface:#f6f5f2;--raised:#ffffff;--sunken:#ecebe6;--ink:#1f2328;--muted:#575e66;--line:#d6d3cc;--line2:#8f8b82;"
    "--accent:#1c5d8a;--accent-weak:#e2edf5;--focus:#1c5d8a;"
    "--running:#0b5aa8;--running-bg:#e3edf9;--succeeded:#1b6837;--succeeded-bg:#e2f0e6;"
    "--failed:#b0261d;--failed-bg:#fae6e3;--lost:#865700;--lost-bg:#f7edd6}"
    "@media (prefers-color-scheme:dark){:root{--surface:#15171a;--raised:#1e2125;--sunken:#101214;--ink:#e9e7e2;--muted:#a2a8b0;"
    "--line:#33373d;--line2:#646a73;--accent:#7db8e2;--accent-weak:#1a2c3a;--focus:#9cccf0;"
    "--running:#80b6f2;--running-bg:#15263a;--succeeded:#78c792;--succeeded-bg:#14291c;--failed:#f28b81;--failed-bg:#3a1916;"
    "--lost:#e2b35e;--lost-bg:#33270e}}"
    "*{box-sizing:border-box}"
    "body{margin:0;font-family:" + SANS + ";font-size:13px;line-height:20px;background:var(--surface);color:var(--ink)}"
    "a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}"
    "a:focus-visible{outline:2px solid var(--focus);outline-offset:2px}summary:focus-visible{outline:2px solid var(--focus);outline-offset:2px}"
    "h1{font-size:22px;line-height:28px;margin:0}h2{font-size:15px;line-height:22px;margin:0}p{margin:0}"
    "button{font:inherit;padding:8px 16px;border:1px solid var(--accent);border-radius:4px;background:var(--accent);"
    "color:var(--raised);cursor:pointer}"
    "input,select,textarea{font:inherit;padding:8px;border:1px solid var(--line2);border-radius:4px;background:var(--raised);color:var(--ink)}"
    "input:focus-visible,select:focus-visible,textarea:focus-visible,button:focus-visible{outline:2px solid var(--focus);outline-offset:2px}"
    "textarea{font-family:" + MONO + ";min-height:96px;resize:vertical}"
    ".lform{display:flex;flex-direction:column;gap:12px;max-width:640px}.lform label{display:flex;flex-direction:column;gap:4px}"
    ".lform input,.lform select,.lform textarea{width:100%;min-width:0}.lform button{align-self:flex-start}"
    ".acts form,form.act{margin:0;display:inline}"
    ".sq{display:inline-block;width:8px;height:8px;background:var(--c);flex:none;align-self:center}"
    ".chip{display:inline-flex;gap:4px;align-items:center;font-weight:600;color:var(--c)}"
    "pre{font-family:" + MONO + ";font-size:13px;background:var(--sunken);border-radius:4px;padding:12px;overflow-x:auto;white-space:pre-wrap;overflow-wrap:anywhere;margin:0}"
    "code{font-family:" + MONO + "}small{font-size:12px;color:var(--muted)}"
    ".bad{color:var(--failed)}.ok{color:var(--succeeded)}"
    ".narrow{max-width:640px;margin:0 auto;padding:24px;display:flex;flex-direction:column;gap:16px}"
    ".mast{display:flex;align-items:center;gap:16px;height:40px;padding:0 16px;background:var(--ink);color:var(--surface)}"
    ".mast .brand{font-weight:600}.mast .end{margin-left:auto;display:flex;align-items:center;gap:16px}"
    ".mast a{color:var(--surface);padding:0 8px}.mast a:focus-visible{outline-color:var(--surface)}"
    ".costs{display:flex;gap:12px}.cost{font-size:12px}"
    ".switch{display:flex}.switch a+a{border-left:1px solid var(--surface)}.switch a.here{font-weight:600;text-decoration:underline}"
    ".wb{display:grid;grid-template-columns:272px minmax(0,1fr) 320px;min-height:calc(100vh - 40px)}.wb>*{min-width:0}"
    "@media (max-width:1200px){.wb{grid-template-columns:232px minmax(0,1fr) 288px}}"
    ".side{background:var(--raised);border-right:1px solid var(--line);padding:16px;display:flex;flex-direction:column;gap:12px}"
    ".nav,.tools,.rows,.foot{display:flex;flex-direction:column;gap:4px}"
    ".foot{margin-top:auto;border-top:1px solid var(--line);padding-top:12px}"
    ".nv,.row{display:flex;align-items:center;gap:8px;padding:4px 8px;border-radius:4px;color:var(--ink)}"
    "a.nv.here,a.row.here{background:var(--accent-weak);font-weight:600}"
    ".row{flex-direction:column;align-items:stretch;gap:0}.r1{display:flex;align-items:center;gap:8px}.r2{font-size:12px;color:var(--muted);overflow-wrap:anywhere}"
    "h3{font-size:12px;line-height:20px;margin:0;font-weight:600;color:var(--muted)}.proj{display:flex;flex-direction:column;gap:4px}"
    ".views{display:flex;gap:16px}.views a[aria-current]{color:var(--ink);font-weight:600}"
    ".nm{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.row .nm{flex:1}"
    ".stg{font-size:12px;color:var(--muted);white-space:nowrap}"
    ".off,.muted{color:var(--muted)}.off{padding:4px 8px}.later{font-size:12px;color:var(--muted)}.more{font-size:12px;color:var(--muted)}"
    ".state-running{--c:var(--running);--bg:var(--running-bg)}.state-succeeded{--c:var(--succeeded);--bg:var(--succeeded-bg)}"
    ".state-failed{--c:var(--failed);--bg:var(--failed-bg)}"
    ".sym{color:var(--c)}"
    ".main{padding:24px;display:flex;flex-direction:column;gap:16px;overflow-wrap:anywhere}"
    ".head{display:flex;align-items:center;gap:12px;flex-wrap:wrap}"
    ".badge{display:inline-flex;gap:4px;padding:0 8px;border-radius:999px;font-size:12px;line-height:20px;font-weight:600;"
    "white-space:nowrap;color:var(--c);background:var(--bg)}"
    ".steps{display:flex;gap:8px;list-style:none;margin:0;padding:0}.steps li{flex:1;min-width:0}"
    ".steps a{display:block;padding:8px 0 0;color:var(--muted)}"
    ".steps .is-done a{border-top:3px solid var(--succeeded);color:var(--ink)}"
    ".steps .is-current a{border-top:3px solid var(--accent);color:var(--ink);font-weight:600}"
    ".steps .is-later a{border-top:3px dashed var(--line2)}"
    ".steps .is-failed a{border-top-color:var(--failed);color:var(--failed)}"
    ".menu>summary{display:flex;align-items:center;min-height:44px;cursor:pointer}"
    ".steps a[aria-current]{outline:2px solid var(--focus);outline-offset:2px}"
    ".card{background:var(--raised);border:1px solid var(--line);border-radius:6px;padding:16px;display:flex;flex-direction:column;gap:12px}"
    ".counts{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin:0}"
    ".counts div{background:var(--sunken);border-radius:4px;padding:4px 8px;min-width:0}"
    ".counts dt{font-size:12px;color:var(--muted)}.counts dd{margin:0;font-size:15px;font-weight:600}"
    ".kv{display:flex;gap:12px;flex-wrap:wrap}.kv span{color:var(--muted)}.kv .done{color:var(--ink);font-weight:600}"
    "progress{display:block;width:100%;height:4px;border:0;border-radius:999px;background:var(--sunken);margin-top:4px;appearance:none}"
    "progress::-webkit-progress-bar{background:var(--sunken);border-radius:999px}"
    "progress::-webkit-progress-value{background:var(--accent);border-radius:999px}progress::-moz-progress-bar{background:var(--accent)}"
    ".pager{display:flex;justify-content:space-between}"
    ".reason{font-family:" + MONO + ";font-size:13px;background:var(--sunken);border:1px solid var(--failed);border-radius:4px;"
    "padding:12px;white-space:pre-wrap;margin:0}"
    ".sec ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px}"
    ".rail{background:var(--raised);border-left:1px solid var(--line);padding:16px;display:flex;flex-direction:column;gap:12px}"
    ".card,.reason{min-width:0;overflow-wrap:anywhere}"
    ".prov{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:4px 16px;margin:0;overflow-wrap:anywhere}"
    ".prov dt{color:var(--muted)}.prov dd{margin:0;min-width:0;overflow-wrap:anywhere}.prov code{display:block}"
    ".pack{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px}.pack li{display:flex;gap:12px;flex-wrap:wrap}"
    ".notices{display:flex;flex-direction:column;gap:12px}"
    ".notice{background:var(--raised);border:1px solid var(--line);border-radius:6px;padding:12px;display:flex;flex-direction:column;gap:8px;min-width:0}"
    ".nhead{display:flex;flex-wrap:wrap;align-items:center;gap:8px}"
    ".level{display:inline-flex;gap:4px;padding:0 8px;border-radius:999px;font-size:12px;line-height:20px;font-weight:600;white-space:nowrap;"
    "color:var(--c);background:var(--bg)}"
    ".when{margin-left:auto;font-size:12px;color:var(--muted);white-space:nowrap}"
    ".fields{display:grid;grid-template-columns:auto minmax(0,1fr);gap:4px 12px;margin:0}"
    ".fields dt{color:var(--muted)}.fields dd{margin:0;min-width:0;overflow-wrap:anywhere}"
    ".acts{display:flex;flex-wrap:wrap;gap:8px}"
    ".sumcards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}"
    ".scard{background:var(--raised);border:1px solid var(--line);border-radius:6px;padding:12px;min-width:0;overflow-wrap:anywhere}"
    ".ct{font-size:12px;line-height:20px;font-weight:400;color:var(--muted)}.cv{font-size:15px;font-weight:600}"
    ".rtabs{display:flex;flex-wrap:wrap;gap:16px;border-bottom:1px solid var(--line)}.rtabs a{padding:4px 0;color:var(--muted)}"
    ".rtabs a[aria-current]{color:var(--ink);font-weight:600;border-bottom:3px solid var(--accent)}"
    ".tbl{width:100%;table-layout:fixed;border-collapse:collapse}"
    ".tbl th,.tbl td{text-align:left;padding:4px 8px;border-bottom:1px solid var(--line);vertical-align:top;min-width:0;overflow-wrap:anywhere}"
    ".soon{background:var(--sunken);color:var(--muted);border-radius:6px;padding:16px;min-width:0}"
    ".otbl code{overflow-wrap:anywhere}.ostat{display:flex;flex-wrap:wrap;align-items:center;gap:8px}"
    "@media (max-width:900px){.wb{grid-template-columns:1fr}.main{order:-2}.rail{order:-1}.costs{display:none}"
    ".counts{grid-template-columns:repeat(4,1fr)}}"
)


def style_source():
    """The CSP source for the stylesheet: the sha256 of exactly the text between <style> and </style>."""
    return "'sha256-%s'" % base64.b64encode(hashlib.sha256(STYLE.encode("utf-8")).digest()).decode("ascii")


def esc(text):
    return html.escape(str(text), quote=True)


def pick_lang(raw):
    """English only for exactly `en`; anything else (missing, unknown, markup) is the default Chinese."""
    return "en" if raw == "en" else "zh"


def stage_of(status):
    """The stage a run belongs to, from its status alone: running, lost and failed are `running`; succeeded is `results`."""
    return "results" if status == "succeeded" else "running"


def pick_stage(raw, default):
    return raw if raw in STAGES else default


TABS = ("tasks", "logs", "info", "config", "metrics")


def pick_tab(raw):
    """The tab named exactly (lower case); anything else is None, which means the first tab."""
    return raw if raw in TABS else None


RESULT_TABS = ("outputs", "info", "tasks", "logs")


def pick_results_tab(raw):
    """The tab of the results stage named exactly; anything else is the first one, Outputs."""
    return raw if raw in RESULT_TABS else "outputs"


def _url(lang, run=None, stage=None, path="/", tab=None, relist=False):
    """A link to a board page: `/` or `/settings` with a query. `lang=en` is kept on every link of an English page. Only the
    Read-again link of the Outputs tab carries `relist`; no other link, and never the page's own refresh, does."""
    query = []
    if run:
        query.append("run=" + urllib.parse.quote(str(run), safe=""))
    if stage:
        query.append("stage=" + stage)
    if tab:
        query.append("tab=" + tab)
    if relist:
        query.append("relist=1")
    if lang == "en":
        query.append("lang=en")
    return esc(path + ("?" + "&".join(query) if query else ""))


def _css(status):
    """The style class of a state: lost looks like failed (the page has three states)."""
    return "failed" if status == "lost" else (status if status in SYMBOLS else "unknown")


def _sym(status):
    return SYMBOLS.get(status, "?")


def _state(t, status):
    return t.get("state_" + str(status), str(status))


def _time(iso):
    """`MM-DD HH:mm` in Asia/Taipei (a fixed +8 hours: Taiwan has no summer time) from the UTC text of the run view."""
    try:
        moment = datetime.datetime.strptime(str(iso), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return "—"
    return (moment + TAIPEI).strftime("%m-%d %H:%M")


def taipei_time(epoch):
    """`MM-DD HH:mm` in Asia/Taipei for an epoch (seconds), or None when there is none."""
    try:
        return (datetime.datetime.fromtimestamp(float(epoch), datetime.timezone.utc) + TAIPEI).strftime("%m-%d %H:%M")
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _later(t):
    return '<span class="later">%s</span>' % esc(t["later"])


def _grey(t, key):
    return '<span class="off">%s %s</span>' % (esc(t[key]), _later(t))


def _more(t, total):
    return '<p class="more">%s</p>' % esc(t["more"] % (total - LIST_CAP)) if total > LIST_CAP else ""


def _first_line(text, cap):
    for line in str(text).splitlines():
        if line.strip():
            line = line.strip()
            return line if len(line) <= cap else line[:cap - 1] + "…"
    return ""


def _done_total(run):
    tasks = run.get("tasks") or {}
    return tasks.get("succeeded", 0) + tasks.get("cached", 0), tasks.get("total", 0)


def _progress(run):
    done, total = _done_total(run)
    return '<progress value="%d" max="%d"></progress>' % (done, total) if total else "<progress></progress>"


def _mast(t, name, lang, run, stage, path="/", tab=None):
    zh_here = "" if lang == "en" else ' class="here"'
    en_here = ' class="here"' if lang == "en" else ""
    return ('<header class="mast"><span class="brand">agentic-bioflow</span><span class="end">'
            '<span class="costs"><span class="cost">%s</span><span class="cost">%s</span></span>'
            '<span class="switch"><a href="%s"%s>中</a><a href="%s"%s>EN</a></span><span class="who">%s</span></span></header>'
            % (esc(t["cost_su"]), esc(t["cost_cloud"]), _url("zh", run, stage, path, tab), zh_here, _url("en", run, stage, path, tab), en_here,
               esc(name)))


def _failure_of(run):
    """The failure record of a failed or lost run as the actions give it (None for any other run)."""
    return run.get(FAILURE) or None


def _detail(t, run):
    """Line 2 of a list row: `stage · detail` (DESIGN.md v2), from the run's own record."""
    status = run["status"]
    if status == "running":
        done, total = _done_total(run)
        return "%s · %d / %d" % (t["row_run"], done, total)
    if status == "succeeded":
        return t["row_results"]
    failure = _failure_of(run) or {}
    seqera = failure.get("status_seqera") or ("unknown" if status == "lost" else "failed")
    if seqera == STOPPED:
        return t["row_stopped"]
    if seqera == "unknown":
        return t["row_site"]
    return "%s · %s" % (t["row_run"], first_failed(failure) or "—")


def _row(t, run, selected_id, lang):
    mark = " here" if run["id"] == selected_id else ""
    return ('<a class="row state-%s%s" href="%s"><span class="r1"><span class="sym">%s</span><span class="nm">%s</span>'
            '<span class="stg">%s</span></span><span class="r2">%s</span></a>'
            % (_css(run["status"]), mark, _url(lang, run["id"]), _sym(run["status"]), esc(run["name"]),
               esc(_state(t, run["status"])), esc(_detail(t, run))))


def _projects(runs):
    """[(project name or None, [runs])] of the first LIST_CAP runs (newest first, as given): a group sits where its newest run is, and
    the runs that have no project name are the last group."""
    found = {}
    for run in runs[:LIST_CAP]:
        found.setdefault(run.get("project"), []).append(run)
    order = [name for name in found if name is not None] + ([None] if None in found else [])
    return [(name, found[name]) for name in order]


def _left(t, runs, selected_id, lang, csrf, here):
    groups = "".join('<section class="proj"><h3>%s</h3><div class="rows">%s</div></section>'
                     % (esc(t["no_project"] if name is None else name), "".join(_row(t, r, selected_id, lang) for r in members))
                     for name, members in _projects(runs))
    body = ('%s%s' % (groups, _more(t, len(runs)))) if runs else '<p class="muted">%s</p>' % esc(t["none_yet"])
    return ('<aside class="side" data-pane="left"><div class="tools"><a class="nv%s" href="%s">%s</a></div><h2>%s</h2>%s'
            '<div class="tools">%s%s%s</div>'
            '<div class="foot"><a class="nv%s" href="%s">%s</a>%s%s'
            '<form method="post" action="/logout"><input type="hidden" name="csrf" value="%s"><button type="submit">%s</button></form>'
            '</div></aside>'
            % (" here" if here == "launch" else "", _url(lang, path="/launch"), esc(t["new_analysis"]), esc(t["mine"]), body,
               _grey(t, "new_project"), _grey(t, "search_projects"), _grey(t, "upload"),
               " here" if here == "settings" else "", _url(lang, path="/settings"), esc(t["settings"]),
               _grey(t, "explorer"), _grey(t, "dashboard"), esc(csrf), esc(t["logout"])))


def _task_card(t, run):
    tasks = run.get("tasks") or {}
    done, total = _done_total(run)
    cells = "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (esc(t["count_" + c]), esc(tasks.get(c, 0))) for c in COUNTS)
    out = ('%s<p class="kv"><span class="done">%d / %d</span></p><p class="kv"><span>%s</span> %s <span>%s</span> %s</p><dl class="counts">%s</dl>'
           % (_progress(run), done, total, esc(t["started"]), esc(_time(run.get("started_at"))), esc(t["ended"]), esc(_time(run.get("ended_at"))), cells))
    if run.get("failure_reason"):
        out += '<pre class="reason">%s</pre>' % esc(run["failure_reason"])
    return out


def _stage_card(t, run, stage, lang="zh", outputs=None, finished=None, user_name=""):
    if stage == "finished" and run["status"] == "succeeded":
        return web_finished.render_finished(lang, run, finished, outputs, user_name)
    if stage == "finished":
        inner = '<p>— <span class="muted">%s</span></p>' % esc(t["not_reached"])
    elif stage in PLACEHOLDER:
        inner = '<p>— <span class="muted">%s</span></p>' % esc(PLACEHOLDER[stage])
    elif stage != "running" and stage_of(run["status"]) != stage:
        inner = '<p>— <span class="muted">%s</span></p>' % esc(t["not_reached"])
    else:
        inner = _task_card(t, run)
    return '<section class="card"><h2>%s</h2>%s</section>' % (esc(t["stage_" + stage]), inner)


def _epoch(iso):
    try:
        return datetime.datetime.strptime(str(iso), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()
    except ValueError:
        return None


def _duration(t, run, now):
    """How long the run took (to its end) or has been going (to now), in the words of the page; `—` when the start is unknown."""
    start = _epoch(run.get("started_at"))
    end = _epoch(run.get("ended_at"))
    end = now if end is None else end
    if start is None or end is None:
        return "—"
    minutes = int(max(0, end - start) // 60)
    if minutes < 1:
        return t["dur_short"]
    return t["dur_hm"] % (minutes // 60, minutes % 60) if minutes >= 60 else t["dur_m"] % minutes


def _current_step(t, run):
    running = sorted(p["name"] for p in run.get("processes") or [] if p.get("running"))
    if not running:
        return "—"
    return esc(running[0]) + (" " + esc(t["more_steps"] % (len(running) - 1)) if len(running) > 1 else "")


class Acts:
    """What the pages need to draw the real buttons of spec 012b: the words, the language and a function that gives the CSRF token of
    one run's buttons. Without one (the pure tests of a single component) no button is drawn."""

    def __init__(self, t, lang, csrf_for):
        self.t, self.lang, self.csrf_for = t, lang, csrf_for

    def form(self, verb, run_id):
        """One button as a small POST form; the person lands on the confirmation page, nothing is sent from here."""
        keep = '<input type="hidden" name="lang" value="en">' if self.lang == "en" else ""
        return ('<form class="act" method="post" action="/act/%s"><input type="hidden" name="run" value="%s">'
                '<input type="hidden" name="csrf" value="%s">%s<button type="submit">%s</button></form>'
                % (verb, esc(run_id), esc(self.csrf_for(run_id)), keep, esc(self.t[{"resume": "resume", "relaunch": "rerun", "cancel": "cancel"}[verb]])))


def _chip(t, status):
    """A status as a small coloured square (its own element, coloured by the style sheet) and the word."""
    return '<span class="chip state-%s"><span class="sq"></span> %s</span>' % (_css(status), esc(t.get("chip_" + str(status), str(status))))


def _clock_hm(iso):
    """`HH:mm` in Asia/Taipei from the UTC text of the run view, or a dash."""
    shown = _time(iso)
    return shown[-5:] if shown != "—" else shown


def _reason_lines(t, failure):
    """The Reason of a failure notice: the last three non-empty lines of Nextflow's own words, each cut to REASON_CAP; without them the
    word for a stopped or silent run, else the first line of the first failed task's message. The page sorts nothing into causes."""
    lines = [x.strip() for x in str(failure.get("failure_reason") or "").splitlines() if x.strip()][-3:]
    if lines:
        return [x if len(x) <= REASON_CAP else x[:REASON_CAP] + "…" for x in lines]
    if failure.get("status_seqera") == STOPPED:
        return [t["r_stopped"]]
    if failure.get("status_seqera") == "unknown":
        return [t["r_site"]]
    tasks = failure.get("failed_tasks") or []
    return [_first_line((tasks[0].get("error_message") if tasks else "") or "", REASON_CAP) or "—"]


def _failure_notice(t, run, acts=None):
    """The one formal notice of a failed or lost run (DESIGN.md v2, Seqera's fields): level and time, Step / Reason / Next, one button
    (the first of the run's actions). It is worked out from the run's own record on every request; empty when the run did not fail."""
    failure = _failure_of(run)
    if failure is None:
        return ""
    lost = run["status"] == "lost"
    step = first_failed(failure)
    verb = (failure.get("actions") or ["relaunch"])[0]
    word = t["resume" if verb == "resume" else "rerun"]
    when = _clock_hm(run.get("last_message_at") if lost else run.get("ended_at"))
    rows = (("f_step", "<code>%s</code>" % esc(step) if step else "—"),
            ("f_reason", "<br>".join(esc(x) for x in _reason_lines(t, failure))),
            ("f_next", esc(word + t["confirm_suffix"])))
    return ('<article class="notice state-failed"><div class="nhead"><span class="level state-failed"><span class="sq"></span> %s</span>'
            '<span class="when">%s</span></div><dl class="fields">%s</dl><div class="acts">%s</div></article>'
            % (esc(t["level_action"]), esc(when), "".join("<dt>%s</dt><dd>%s</dd>" % (esc(t[k]), v) for k, v in rows),
               acts.form(verb, run["id"]) if acts else ""))


def first_failed(run):
    """The name of the first failed task of a run view or of its failure record, or None."""
    tasks = run.get("failed_tasks") or []
    return tasks[0]["name"] if tasks else None


def _sum_cards(t, run, now):
    stopped = run.get("status") in ("failed", "lost")
    cards = (((t["card_stopped_at"], esc(first_failed(run) or "—")) if stopped else (t["card_step"], _current_step(t, run))), (t["card_duration"], esc(_duration(t, run, now))),
             (t["card_compute"], esc(run.get("compute_env") or "—")), (t["card_cost"], esc(t["cost_su"])))
    return _cards(cards)


def _cards(cards):
    return '<section class="sumcards">%s</section>' % "".join('<div class="scard"><h2 class="ct">%s</h2><p class="cv">%s</p></div>' % (esc(k), v)
                                                              for k, v in cards)


def _results_cards(t, run, now, outputs):
    """The four cards of the results stage, in the words and the way of the running stage's cards: steps done, time taken, where it ran
    (from the output record, when there is one) and the cost, which is a dash until the site gives one."""
    done, total = _done_total(run)
    where = (outputs or {}).get("compute_env") or "—"
    return _cards(((t["card_done"], "%d / %d" % (done, total)), (t["card_duration"], esc(_duration(t, run, now))),
                   (t["card_compute"], esc(where)), (t["card_cost"], esc(t["cost_su"]))))


def _size(value):
    return esc(value if isinstance(value, int) else "—")


def _outputs_body(t, lang, run_id, out):
    """The Outputs tab, from the answer of the action `run_outputs`: loading, ready (a table, or a line when the folder is empty), error,
    or unavailable. Each state has a symbol and words; the colour only helps. Names are plain text: nothing here downloads or changes a file."""
    out = out or {}
    state = out.get("state") if out.get("found") is not False else "unavailable"
    again = '<a href="%s">%s</a>' % (_url(lang, run_id, "results", tab="outputs", relist=True), esc(t["o_relist"]))
    reason = plain_reason(out.get("reason") or "", lang) if out.get("reason") else "—"
    why = '<dl class="fields"><dt>%s</dt><dd>%s</dd></dl>' % (esc(t["f_reason"]), esc(reason))
    if state == "loading":
        return '<p class="ostat state-running"><span class="sym">⟳</span> %s <small>%s</small></p>' % (esc(t["o_loading"]), esc(t["o_auto"]))
    if state == "error":
        return '<p class="ostat state-failed"><span class="sym">✗</span> %s</p>%s<p>%s</p>' % (esc(t["o_failed"]), why, again)
    if state != "ready":
        return '<p class="ostat muted"><span>—</span> %s</p>%s' % (esc(t["o_none"]), why)
    when = taipei_time(out.get("listed_at"))
    head = '<p class="ostat"><span>%s %s</span> %s</p>' % (esc(t["o_read_at"]), esc(when[-5:] if when else "—"), again)
    files = sorted(out.get("files") or [], key=lambda f: (f.get("type") != "dir", f.get("name") or ""))
    if not files:
        return head + '<p class="ostat muted"><span>—</span> %s</p>' % esc(t["o_empty"])
    th = "".join("<th>%s</th>" % esc(t[k]) for k in ("th_name", "th_type", "th_size", "th_mod"))
    rows = "".join("<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td></tr>"
                   % (esc(f.get("name") or "—"), esc(t.get("ty_" + str(f.get("type")), t["ty_other"])), _size(f.get("size")),
                      esc(_time(f.get("modified")))) for f in files)
    return head + '<table class="tbl otbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (th, rows)


def _results_body(t, lang, run, tab, now, outputs):
    """The results stage of a succeeded run: four cards, four tabs (Outputs, Run info, Tasks, Logs; the last three are the running
    stage's own bodies) and the things that come later as grey words, not links."""
    later = '<p class="kv">%s</p>' % "".join(_grey(t, k) for k in ("ph_report", "ph_multiqc", "ph_metrics", "ph_download"))
    links = "".join('<a href="%s"%s>%s</a>' % (_url(lang, run["id"], None, tab=k), ' aria-current="page"' if k == tab else "", esc(t["tab_" + k]))
                    for k in RESULT_TABS)
    body = _outputs_body(t, lang, run["id"], outputs) if tab == "outputs" else tab_body(t, lang, run, tab)
    return '%s%s<nav class="rtabs">%s</nav>%s' % (_results_cards(t, run, now, outputs), later, links, body)


def _tasks_bar(t, run):
    tasks = run.get("tasks") or {}
    cells = "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (esc(t["count_" + c]), esc(tasks.get(c, 0))) for c in COUNTS)
    done, total = _done_total(run)
    facts = ('<p class="kv"><span class="done">%d / %d</span></p><p class="kv"><span>%s</span> %s <span>%s</span> %s</p>'
             % (done, total, esc(t["started"]), esc(_time(run.get("started_at"))), esc(t["ended"]), esc(_time(run.get("ended_at")))))
    return '<section class="card">%s%s<dl class="counts">%s</dl></section>' % (_progress(run), facts, cells)


def tab_body(t, lang, run, tab):
    """The content of one tab of the running stage page. Logs, Configuration and Metrics are grey panels until their actions exist."""
    if tab == "tasks":
        tasks = run.get("failed_tasks") or []
        if not tasks:
            return '<p class="muted">%s</p>' % esc(t["no_failed_tasks"])
        head = "".join("<th>%s</th>" % esc(t[k]) for k in ("th_name", "th_exit", "th_message", "th_workdir"))
        body = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                       % (esc(f.get("name") or "—"), esc("—" if f.get("exit_code") is None else f["exit_code"]),
                          esc(_first_line(f.get("error_message") or "", REASON_CAP) or "—"), esc(f.get("workdir") or "—")) for f in tasks)
        return '<table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (head, body)
    if tab == "info":
        status = run["status"]
        rows = [(t["i_id"], run["id"]), (t["i_name"], run["name"]), (t["i_status"], "%s %s" % (_sym(status), _state(t, status))),
                (t["started"], _time(run.get("started_at"))), (t["ended"], _time(run.get("ended_at")))]
        if run.get("cancel_requested_at"):
            rows.append((t["i_cancel"], _time(run["cancel_requested_at"])))
        full = '<pre class="reason">%s</pre>' % esc(run["failure_reason"]) if run.get("failure_reason") else ""     # the whole text lives here, not on the Tasks tab
        return '<dl class="fields">%s</dl>%s' % ("".join("<dt>%s</dt><dd>%s</dd>" % (esc(k), esc(v)) for k, v in rows), full)
    return '<section class="soon"><p>%s</p></section>' % esc(t["later"])


def _running_body(t, selected, lang, tab_param, stage_param, now, acts=None):
    tab = tab_param or "tasks"
    links = "".join('<a href="%s"%s>%s</a>' % (_url(lang, selected["id"], stage_param, tab=k), ' aria-current="page"' if k == tab else "",
                                               esc(t["tab_" + k])) for k in TABS)
    return '%s%s<nav class="rtabs">%s</nav>%s' % (_sum_cards(t, selected, now), _tasks_bar(t, selected), links, tab_body(t, lang, selected, tab))


def _run_page(t, selected, stage_param, lang, tab_param=None, now=None, acts=None, flash=None, outputs=None, finished=None, user_name=""):
    own = stage_of(selected["status"])
    current = pick_stage(stage_param, own)
    explicit = pick_stage(stage_param, None)
    index, rank = STAGES.index(current), STAGES.index(own)
    cells = []
    for n, s in enumerate(STAGES):
        kind = "is-done" if n < rank else ("is-current" if n == rank else "is-later")
        mark = ' aria-current="step"' if s == current else ""
        label = ("✓ " if kind == "is-done" else "") + t["stage_" + s]
        if s == "running" and selected["status"] in ("failed", "lost"):
            kind, label = kind + " is-failed", "✗ " + t["stage_running_failed"]
        if s == "finished" and selected["status"] != "succeeded" and s != current:      # a run that has not succeeded has no finished stage to open
            cells.append('<li class="%s" data-step="%s"><span>%s</span></li>' % (kind, s, esc(label)))
            continue
        cells.append('<li class="%s" data-step="%s"><a href="%s"%s>%s</a></li>' % (kind, s, _url(lang, selected["id"], s, tab=tab_param), mark, esc(label)))
    prev_ = ('<a rel="prev" href="%s">%s</a>' % (_url(lang, selected["id"], STAGES[index - 1], tab=tab_param), esc(t["prev"]))) \
        if index > 0 else "<span></span>"
    next_ = ('<a rel="next" href="%s">%s</a>' % (_url(lang, selected["id"], STAGES[index + 1], tab=tab_param), esc(t["next"]))) \
        if index < len(STAGES) - 1 else "<span></span>"
    status = selected["status"]
    badge = '<span class="badge state-%s">%s %s</span>' % (_css(status), _sym(status), esc(_state(t, status)))
    running = current == "running"
    buttons = ("".join(acts.form(verb, selected["id"]) for verb in ("resume", "relaunch", "cancel")) if acts else "") if running else ""
    quick = '<a href="%s">%s</a>' % (esc("/launch?from=" + urllib.parse.quote(str(selected["id"]), safe="") + ("&lang=en" if lang == "en" else "")),
                                    esc(t["quick"])) if running else ""
    menu = '<details class="menu"><summary>%s</summary>%s%s</details>' % (esc(t["menu_more"]), buttons, quick) if running else ""
    if running:
        inner = _running_body(t, selected, lang, tab_param, explicit, now, acts)
    elif current == "results" and status == "succeeded":
        inner = _results_body(t, lang, selected, pick_results_tab(tab_param), now, outputs)
    else:
        inner = _stage_card(t, selected, current, lang, outputs, finished, user_name)
    note = '<p class="bad" role="alert">%s</p>' % esc(flash) if flash else ""
    views = '<nav class="views"><a href="%s" aria-current="page">%s</a>%s</nav>' % (_url(lang, selected["id"]), esc(t["main_window"]), _grey(t, "terminal"))
    return ('<main class="main" data-pane="middle"><div class="head"><h1>%s</h1>%s%s</div>%s%s'
            '<ol class="steps" data-current="%s">%s</ol>%s<p class="pager">%s%s</p></main>'
            % (esc(selected["name"]), badge, menu, views, note, current, "".join(cells), inner, prev_, next_))


def _settings_page(t):
    secs = []
    for head, entries in SETTINGS:
        inner = "<ul>%s</ul>" % "".join("<li>%s</li>" % _grey(t, e) for e in entries) if entries else "<p>%s</p>" % _later(t)
        secs.append('<section class="card sec"><h2>%s</h2>%s</section>' % (esc(t[head]), inner))
    return '<main class="main" data-pane="middle"><h1>%s</h1>%s</main>' % (esc(t["settings"]), "".join(secs))


def _right(t, selected, acts=None):
    """The right column: the formal notices of the selected analysis only (this version: its failure), then the grey line for the chat."""
    if selected is None:
        return '<aside class="rail" data-pane="right"><p class="muted">%s</p><p class="muted">—</p></aside>' % esc(t["this_analysis"])
    notice = _failure_notice(t, selected, acts)
    inner = '<div class="notices">%s</div>' % notice if notice else '<p class="muted">%s</p>' % esc(t["no_notices"])
    return ('<aside class="rail" data-pane="right"><p class="muted">%s</p><h2>%s</h2>%s<p>%s</p></aside>'
            % (esc(t["this_analysis"]), esc(selected["name"]), inner, _grey(t, "ask_here")))


def document(title, body, refresh=False, board=False, lang="zh", refresh_url=None):
    """A whole page. Only the board asks for the meta refresh; a page that is not the board gets the narrow single column.
    `refresh_url` (already escaped) is the address the refresh goes to, when it must not be the address the page was asked for."""
    head = ("<meta http-equiv=\"refresh\" content=\"%d%s\">" % (REFRESH_SECONDS, ";url=" + refresh_url if refresh_url else "")) if refresh else ""
    wrapped = body if board else '<main class="narrow">%s</main>' % body
    return ("<!doctype html><html lang=\"%s\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">%s"
            "<title>%s</title><style>%s</style></head><body>%s</body></html>"
            % ("en" if lang == "en" else "zh-Hant", head, esc(title), STYLE, wrapped))


def default_run(runs):
    """The id of the run `/` opens when no run is named: the newest failed or lost one (it needs the person), else the newest; None when
    there is no run. `runs` are newest first, as list_runs gives them, and only the caller's own."""
    for run in runs:
        if run["status"] in ("failed", "lost"):
            return run["id"]
    return runs[0]["id"] if runs else None


def _empty_page(t, lang):
    return ('<main class="main" data-pane="middle"><p>%s</p><p><a class="nv" href="%s">%s</a></p></main>'
            % (esc(t["no_analyses"]), _url(lang, path="/launch"), esc(t["new_analysis"])))


def _frame(name, csrf, runs, lang, here, middle, right, run=None, stage=None, path="/", refresh=False, tab=None, refresh_url=None):
    lang = pick_lang(lang)
    t = STRINGS[lang]
    body = '%s<div class="wb">%s%s%s</div>' % (_mast(t, name, lang, run, stage, path, tab), _left(t, runs, run, lang, csrf, here), middle(t, lang),
                                                right(t, lang))
    return document(t["title"], body, refresh=refresh, board=True, lang=lang, refresh_url=refresh_url)


def render_board(name, csrf, runs, selected=None, stage_param=None, lang="zh", tab_param=None, now=None, act_csrf=None, flash=None, outputs=None, finished=None):
    """GET /: the page of a logged-in user. `runs` are newest first (as list_runs gives them, with their `failure`); `selected` is the
    detail of one run (get_run, with its `failure`), or None for the empty page of a person with no run. `act_csrf(run_id)` gives the CSRF
    token of that run's buttons (spec 012b); without it no button is drawn. `flash` is one plain line of refusal shown at the top of the
    run page; a page with one does not reload itself, because it is the answer to a POST."""
    run_id = selected["id"] if selected is not None else None
    stage = pick_stage(stage_param, None) if selected is not None else None
    tab = None      # `tab` belongs to the running stage page only; on any other page it is ignored
    if selected is not None and pick_stage(stage_param, stage_of(selected["status"])) == "running":
        tab = pick_tab(tab_param)
    refresh_url = None
    if selected is not None and selected["status"] == "succeeded" and pick_stage(stage_param, "results") == "results":
        tab = pick_results_tab(tab_param)      # the results stage has its own tabs
        if tab == "outputs":      # the page reloads itself to the address without `relist`, so a Read-again click is not repeated every 15 seconds
            refresh_url = _url(pick_lang(lang), run_id, stage, tab="outputs")
    acts = lambda t, lang_: Acts(t, lang_, act_csrf) if act_csrf else None
    middle = (lambda t, lang_: _run_page(t, selected, stage_param, lang_, tab, now, acts(t, lang_), flash, outputs, finished, name)) if selected is not None         else (lambda t, lang_: _empty_page(t, lang_))
    return _frame(name, csrf, runs, lang, "run", middle, lambda t, lang_: _right(t, selected, acts(t, lang_)), run_id, stage,
                  refresh=not flash, tab=tab, refresh_url=refresh_url)


# ---- spec 012b: the launch form -----------------------------------------------------------------------------------------------------------

PARAM_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\Z")
PARAM_INT = re.compile(r"^-?\d+\Z")
PARAM_FLOAT = re.compile(r"^-?\d+\.\d+([eE][-+]?\d+)?\Z")
PARAM_STARTS = "[{&*|>!%@"           # a value that begins with one of these is a list, a mapping or another YAML construct, not a plain value


def parse_params(text, t):
    """({name: value}, [error lines]) from the parameter box: one `name: value` per line, blank lines ignored. A value is plain text, a
    number or true/false; a list, a mapping or an empty value is refused, naming the parameter."""
    out, errors = {}, []
    for raw in str(text or "").splitlines():
        if not raw.strip():
            continue
        key, colon, value = raw.partition(":")
        key, value = key.strip(), value.strip()
        if not colon or raw[:1].isspace() or not PARAM_KEY.match(key):
            errors.append(t["e_param_line"] % raw.strip()[:60])
        elif key in out:
            errors.append(t["e_param_dup"] % key)
        elif not value or value[0] in PARAM_STARTS:
            errors.append(t["e_param_scalar"] % key)
        elif len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            out[key] = value[1:-1]
        elif value.lower() in ("true", "false"):
            out[key] = value.lower() == "true"
        elif PARAM_INT.match(value):
            out[key] = int(value)
        elif PARAM_FLOAT.match(value):
            out[key] = float(value)
        else:
            out[key] = value
    return out, errors


def params_text(params):
    """The parameter box as parse_params reads it back: a text that looks like a number or true/false is quoted, so it stays text."""
    lines = []
    for key, value in (params or {}).items():
        if isinstance(value, bool):
            shown = "true" if value else "false"
        elif isinstance(value, (int, float)):
            shown = str(value)
        else:
            shown = " ".join(str(value).split())
            if (not shown or PARAM_INT.match(shown) or PARAM_FLOAT.match(shown) or shown.lower() in ("true", "false")
                    or shown[0] in PARAM_STARTS or shown[0] in "\"'"):
                shown = '"%s"' % shown.replace('"', "'")
        lines.append("%s: %s" % (key, shown))
    return "\n".join(lines)


CJK = re.compile(r"[⺀-鿿＀-￯]")
LATIN_PAREN = re.compile(r"\(([^()]*)\)\s*$")
PATH_LIKE = re.compile(r"(?<![\w.-])(/[^\s,;)）]+)")


def plain_reason(message, lang):
    """One plain line out of a refusal of the action layer. Those read `中文 (English)`: the page keeps the half of its own language. Anything
    that looks like a path of the machine is cut (nothing here names a folder), and a message with no English half is replaced by a general
    English line on the English page."""
    t = STRINGS[pick_lang(lang)]
    text = str(message or "").strip()
    m = LATIN_PAREN.search(text)
    if lang == "en":
        body = re.sub(r"^未[^：:]{1,6}[：:]\s*", "", text)
        text = m.group(1).strip() if m else ("" if CJK.search(body) else body)
        text = (text[:1].upper() + text[1:]) if text else t["r_generic"]
    elif m:
        text = text[:m.start()].strip() or text
    text = PATH_LIKE.sub("…", text)
    text = re.sub(r"\s+", " ", text)
    return text[:300] + ("" if text.endswith((".", "。")) else ("." if lang == "en" else "。"))


def render_launch(name, csrf, runs, values, errors, notes, sheets, envs, token, lang="zh", source=None):
    """GET /launch (and the answer to a POST that did not pass): one plain form. `values` are what to put in the boxes; `errors` are lines
    of what is wrong (each is its own line); `notes` are plain muted lines (where the boxes were filled from); `sheets` are the names the
    person may choose from, `envs` the environments that are theirs; `token` is the form's CSRF token. `source` is
    (run id, name, status, 'MM-DD HH:mm' or None) of the run a quick launch started from."""
    lang = pick_lang(lang)
    t = STRINGS[lang]

    def box(label, name_, value, required):
        return '<label>%s<input name="%s" value="%s"%s></label>' % (esc(label), name_, esc(value), " required" if required else "")

    def choose(label, name_, options, chosen, empty):
        opts = "".join('<option value="%s"%s>%s</option>' % (esc(o), " selected" if o == chosen else "", esc(o)) for o in options) \
            or '<option value="" disabled selected>—</option>'
        return '<label>%s<select name="%s" required>%s</select></label>%s' % (esc(label), name_, opts, "" if options else '<p class="muted">%s</p>' % esc(empty))
    lines = "".join('<p class="bad" role="alert">%s</p>' % esc(e) for e in errors) + "".join('<p class="muted">%s</p>' % esc(n) for n in notes)
    if source:
        run_id, run_name, status, when = source
        lines += ('<p class="from"><a href="%s">%s</a> %s %s</p>'
                  % (_url(lang, run_id), esc(run_name), _chip(t, status), esc(when) if when else ""))
    form = ('<form class="lform" method="post" action="/launch"><input type="hidden" name="csrf" value="%s">%s%s%s%s%s%s%s'
            '<button type="submit">%s</button></form>'
            % (esc(token), '<input type="hidden" name="lang" value="en">' if lang == "en" else "",
               box(t["l_pipeline"], "pipeline", values.get("pipeline", ""), True),
               box(t["l_revision"], "revision", values.get("revision", ""), True),
               box(t["l_run_name"], "run_name", values.get("run_name", ""), True),
               choose(t["l_samplesheet"], "samplesheet", sheets, values.get("samplesheet"), t["l_no_sheet"]),
               choose(t["l_ce"], "ce_name", envs, values.get("ce_name"), t["l_no_ce"]),
               '<label>%s<textarea name="params" rows="5">%s</textarea></label>' % (esc(t["l_params"]), esc(values.get("params", ""))),
               esc(t["l_submit"])))
    middle = lambda t_, lang_: ('<main class="main" data-pane="middle"><h1>%s</h1><p class="muted">%s</p>%s%s</main>'
                                % (esc(t["launch_title"]), esc(t["launch_intro"]), lines, form))
    return _frame(name, csrf, runs, lang, "launch", middle, lambda t_, lang_: _right(t_, None), path="/launch")


def render_settings(name, csrf, runs, lang="zh"):
    """GET /settings: the same frame, and a middle column of sections that are all still to come."""
    return _frame(name, csrf, runs, lang, "settings", lambda t, lang_: _settings_page(t), lambda t_, lang_: _right(t_, None), path="/settings")


def render_not_found(name, lang="zh"):
    """The 404 of the board: the same bytes for a missing run and for somebody else's, and it never repeats the requested id."""
    lang = pick_lang(lang)
    t = STRINGS[lang]
    body = ('%s<main class="main"><h1>%s</h1><p>%s</p><p><a href="%s">%s</a></p></main>'
            % (_mast(t, name, lang, None, None), esc(t["not_found_title"]), esc(t["not_found_body"]), _url(lang), esc(t["back"])))
    return document(t["title"], body, board=True, lang=lang)
