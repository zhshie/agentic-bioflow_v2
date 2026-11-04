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
    "plain": "/data/run1",
    "all_allowed_chars": "/a/B_c.d@e+f=g:h,i-j/k9",
    "dot_component": "/data/./run1",
    "trailing_slash": "/data/run1/",
    "double_slash": "/data//run1",
    "dots_in_name": "/data/a..b/c",
    "hidden_dir": "/data/.cache",
    # '..'
    "dotdot_alone": "..",
    "dotdot_leading": "../etc",
    "dotdot_middle": "/data/../etc",
    "dotdot_trailing": "/data/..",
    "dotdot_absolute_root": "/..",
    # relative / empty / type
    "relative": "data/run1",
    "relative_dot": "./run1",
    "empty": "",
    "none": None,
    "bytes": b"/data",
    "int": 7,
    "list": ["/data"],
    # very long
    "len_at_limit": "/" + "a" * 1023,
    "len_over_limit": "/" + "a" * 1024,
    "len_far_over_limit": "/" + "a" * 100000,
    "long_and_bad_chars": "/" + "a b" * 2000,
    "long_and_dotdot": "/" + "a/" * 600 + "..",
    # characters outside the allow-list
    "space": "/data/run 1",
    "tab": "/data/run\t1",
    "quote": "/data/'x'",
    "double_quote": '/data/"x"',
    "semicolon": "/data/x;rm",
    "dollar": "/data/$HOME",
    "backtick": "/data/`id`",
    "pipe": "/data/a|b",
    "ampersand": "/data/a&b",
    "backslash": "/data\\run1",
    "glob": "/data/*",
    "tilde": "~/run1",
    "nul": "/data/a\x00b",
    "non_ascii": "/data/資料",
    "emoji": "/data/\U0001F9EC",
    "non_ascii_digit": "/data/٣",
    # trailing / embedded newline
    "trailing_newline": "/data/run1\n",
    "trailing_crlf": "/data/run1\r\n",
    "leading_newline": "\n/data/run1",
    "embedded_newline": "/data/a\nb",
    "only_newline": "\n",
    "dotdot_and_newline": "/data/..\n",
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
