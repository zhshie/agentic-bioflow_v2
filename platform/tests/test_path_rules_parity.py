# Nothing existing: the platform and the agent each keep their own copy of the path rule on purpose; this keeps the two copies agreeing.
"""The platform's path rule and the agent's path rule must give the same answer for the same input.

abf_station.rules.path_problem is a second lock written separately from
abf_platform.compute_envs.path_problem (rules.py header). Separate code is only safe while the
two stay equal, so the same inputs go to both and the answers are compared.
"""
import pytest

from abf_platform import compute_envs
from abf_station import rules

CASES = {
    # legal
    "root": "/",
    "plain": "/work/run1",
    "all_allowed_chars": "/a/B_c.d@e+f=g:h,i-j/k9",
    "dot_component": "/work/./run1",
    "trailing_slash": "/work/run1/",
    "double_slash": "/work//run1",
    "dots_in_name": "/work/a..b/c",
    "hidden_dir": "/work/.cache",
    # '..'
    "dotdot_alone": "..",
    "dotdot_leading": "../etc",
    "dotdot_middle": "/work/../etc",
    "dotdot_trailing": "/work/..",
    "dotdot_absolute_root": "/..",
    # relative / empty / type
    "relative": "work/run1",
    "relative_dot": "./run1",
    "empty": "",
    "none": None,
    "bytes": b"/work",
    "int": 7,
    "list": ["/work"],
    # very long
    "len_at_limit": "/" + "a" * 1023,
    "len_over_limit": "/" + "a" * 1024,
    "len_far_over_limit": "/" + "a" * 100000,
    "long_and_bad_chars": "/" + "a b" * 2000,
    "long_and_dotdot": "/" + "a/" * 600 + "..",
    # characters outside the allow-list
    "space": "/work/run 1",
    "tab": "/work/run\t1",
    "quote": "/work/'x'",
    "double_quote": '/work/"x"',
    "semicolon": "/work/x;rm",
    "dollar": "/work/$HOME",
    "backtick": "/work/`id`",
    "pipe": "/work/a|b",
    "ampersand": "/work/a&b",
    "backslash": "/work\\run1",
    "glob": "/work/*",
    "tilde": "~/run1",
    "nul": "/work/a\x00b",
    "non_ascii": "/work/資料",
    "emoji": "/work/\U0001F9EC",
    "non_ascii_digit": "/work/٣",
    # trailing / embedded newline
    "trailing_newline": "/work/run1\n",
    "trailing_crlf": "/work/run1\r\n",
    "leading_newline": "\n/work/run1",
    "embedded_newline": "/work/a\nb",
    "only_newline": "\n",
    "dotdot_and_newline": "/work/..\n",
}


def test_max_path_is_the_same():
    assert rules.MAX_PATH == compute_envs.MAX_PATH


@pytest.mark.parametrize("name", sorted(CASES))
def test_same_answer(name):
    value = CASES[name]
    assert rules.path_problem(value) == compute_envs.path_problem(value), (
        "station and platform disagree on %r" % (value if not isinstance(value, str) or len(value) < 80 else name))


def test_table_is_not_vacuous():
    """Both copies returning None for everything would also be 'equal'; pin that the table exercises each code."""
    seen = {compute_envs.path_problem(v) for v in CASES.values()}
    assert seen == {None, "type", "empty", "long", "chars", "dotdot", "relative"}
    assert compute_envs.path_problem(CASES["trailing_newline"]) == "chars"
    assert rules.path_problem(CASES["trailing_newline"]) == "chars"
