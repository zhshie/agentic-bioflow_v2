# Nothing existing: test_cli.py and test_dataset_cli.py check what each command does; no test checks that the module description lists the subcommands registered in build_parser.
"""The one-line command list in abf_platform.cli.__doc__ must name every command."""
import argparse
import re

from abf_platform import cli


def _choices(parser):
    if not parser._subparsers:
        return {}
    return dict(parser._subparsers._group_actions[0].choices)


def _launch_commands():
    """The commands abf_launch registers into the same parser (the hand-off record ones)."""
    from abf_launch import cli as launch_cli
    p = argparse.ArgumentParser()
    launch_cli.add_commands(p.add_subparsers(dest="command"))
    return set(_choices(p))


def _doc_groups():
    text = re.sub(r"^abf-platform:\s*", "", cli.__doc__.strip())
    groups = {}
    for seg in text.split(" | "):
        seg = seg.strip()
        name = seg.split(None, 1)[0]
        rest = re.sub(r"\s*\[[^\]]*\]", "", seg[len(name):].strip())
        lst = rest.split(None, 1)[0] if rest else ""
        groups[name] = {n for n in lst.split("|") if n}
    return groups


def test_every_top_level_command_is_named_in_the_doc():  # TC-001
    groups = _doc_groups()
    # The abf_launch hand-off record commands are left out on purpose: the plan (ruling 1)
    # drops the sentence that pointed at them and adds no new one.
    skip = _launch_commands()
    missing = [n for n in _choices(cli.build_parser()) if n not in groups and n not in skip]
    assert not missing, f"not in the module description: {missing}"


def test_every_nested_command_is_named_in_the_doc():  # TC-002
    groups = _doc_groups()
    skip = _launch_commands()
    missing = []
    for top, sub in _choices(cli.build_parser()).items():
        # ce is skipped on purpose: the description says "ce ..." so users read `ce --help`.
        if top == "ce" or top in skip:
            continue
        for name in _choices(sub):
            if name not in groups.get(top, set()):
                missing.append(f"{top} {name}")
    assert not missing, f"not in the module description: {missing}"


def test_doc_has_no_dangling_count():  # TC-006
    assert "four commands" not in cli.__doc__


def test_doc_keeps_core_commands():  # TC-009
    groups = _doc_groups()
    for name in ("serve", "web", "token", "mcp", "rebuild"):
        assert name in groups
