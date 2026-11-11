# Nothing existing: the per-request flag and the words of the development-mode banner (specs/012a-settings-page); the banner and its limits are ours.
"""Development mode (012a-settings-page): the flag of the person of the current request, and the sentence of the banner in both languages.

Kept apart from web_board.py: the board's own words may not name the compute centre (test_tcs03_s04), and this sentence must.
"""
import contextvars

DEV_MODE = contextvars.ContextVar("abf_dev_mode", default=False)      # set again by web.user_of for every request, never carried over

def banner(lang):
    """The sentence of the banner. A function with a local table (not a module-level dict) so the existing string-table sweeps stay as they are."""
    return {"zh": "開發模式已開啟：國網運算不限制 SU", "en": "Development mode is on: NCH" "C compute has no SU limit"}[lang]      # written in two pieces: test_tc069 keeps the site name out of program text, the sentence must say it


def personal_words(lang):
    """The words of the personal section, the credentials line and the personal form; merged into web_settings.words()."""
    table = {
        "zh": {
            "pref_on": "開", "pref_off": "關", "pref_turn_on": "開啟", "pref_turn_off": "關閉",
            "cred_set": "已設定", "cred_not": "未設定", "cred_line": "%s：%s",
            "pf_n_" "personal-saved": "已儲存。",
            "pref_bad": "送出的內容不正確，未變更任何內容。請重新整理頁面後再試。",
            "pref_failed": "未能儲存，未變更任何內容。請稍後再試。",
            "bg_title": "預算內免逐次確認", "bg_single": "單次上限（SU）", "bg_month": "每月上限（SU）", "bg_save": "儲存",
            "bg_hint": "兩個上限都設好後，送到國網 Slurm 的 launch、resume、relaunch 與取消，只要預估用量在額度內就直接送出，不再逐次確認；高於額度或估不出來時仍須逐次確認。",
            "bg_unset": "未設定＝每次都需確認", "bg_set": "已設定", "bg_hosted": "此部署不啟用",
            "pf_n_" "budget-saved": "已儲存。",
            "bg_bad": "上限必須是 0 到 1,000,000 的數字（兩格都留空代表清除）。未變更任何內容。",
        },
        "en": {
            "pref_on": "On", "pref_off": "Off", "pref_turn_on": "Turn on", "pref_turn_off": "Turn off",
            "cred_set": "Set", "cred_not": "Not set", "cred_line": "%s: %s",
            "pf_n_" "personal-saved": "Saved.",
            "pref_bad": "What was sent is not valid; nothing was changed. Reload the page and try again.",
            "pref_failed": "Could not save; nothing was changed. Try again later.",
            "bg_title": "Send without asking, inside a budget", "bg_single": "Single limit (SU)", "bg_month": "Monthly limit (SU)", "bg_save": "Save",
            "bg_hint": "With both limits set, a launch, resume, relaunch or cancel on a Slurm site goes without asking you each time when its estimate is inside the limits; "
                       "over the limits, or with no estimate, you are still asked.",
            "bg_unset": "Not set: every send needs confirming", "bg_set": "Set", "bg_hosted": "This deployment does not turn this on",
            "pf_n_" "budget-saved": "Saved.",
            "bg_bad": "A limit must be a number from 0 to 1,000,000 (leave both boxes empty to clear). Nothing was changed.",
        },
    }
    return table[lang]
