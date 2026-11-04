# Nothing existing: the per-request flag and the words of the development-mode banner (specs/012a-settings-page); the banner and its limits are ours.
"""Development mode (012a-settings-page): the flag of the person of the current request, and the sentence of the banner in both languages.

Kept apart from web_board.py: the board's own words may not name the compute centre (test_tcs03_s04), and this sentence must.
"""
import contextvars

DEV_MODE = contextvars.ContextVar("abf_dev_mode", default=False)      # set again by web.user_of for every request, never carried over

BANNER = {
    "zh": "開發模式已開啟：國網運算不限制 SU",
    "en": "Development mode is on: NCHC compute has no SU limit",
}
