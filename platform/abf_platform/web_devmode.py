# Nothing existing: the per-request flag and the words of the development-mode banner (specs/012a-settings-page); the banner and its limits are ours.
"""Development mode (012a-settings-page): the flag of the person of the current request, and the sentence of the banner in both languages.

Kept apart from web_board.py: the board's own words may not name the compute centre (test_tcs03_s04), and this sentence must.
"""
import contextvars

DEV_MODE = contextvars.ContextVar("abf_dev_mode", default=False)      # set again by web.user_of for every request, never carried over

def banner(lang):
    """The sentence of the banner. A function with a local table (not a module-level dict) so the existing string-table sweeps stay as they are."""
    return {"zh": "開發模式已開啟：國網運算不限制 SU", "en": "Development mode is on: NCHC compute has no SU limit"}[lang]


def personal_words(lang):
    """The words of the personal section, the credentials line and the personal form; merged into web_settings.words()."""
    table = {
        "zh": {
            "pref_on": "開", "pref_off": "關", "pref_turn_on": "開啟", "pref_turn_off": "關閉",
            "cred_set": "已設定", "cred_not": "未設定", "cred_line": "%s：%s",
            "pf_n_personal-saved": "已儲存。",
            "pref_bad": "送出的內容不正確，未變更任何內容。請重新整理頁面後再試。",
            "pref_failed": "未能儲存，未變更任何內容。請稍後再試。",
        },
        "en": {
            "pref_on": "On", "pref_off": "Off", "pref_turn_on": "Turn on", "pref_turn_off": "Turn off",
            "cred_set": "Set", "cred_not": "Not set", "cred_line": "%s: %s",
            "pf_n_personal-saved": "Saved.",
            "pref_bad": "What was sent is not valid; nothing was changed. Reload the page and try again.",
            "pref_failed": "Could not save; nothing was changed. Try again later.",
        },
    }
    return table[lang]
