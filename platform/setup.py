# Not a pyproject-only setting: package-data cannot reach a folder outside platform/, so this build step copies the repository's one skills/ folder into the package.
"""Build hook for abf-platform (spec 009g): the wheel carries abf_platform/skills/ as a copy of <repo>/skills.

Everything else about the package is in pyproject.toml. The copy is made at build time and is never
committed (.gitignore); a test builds a wheel and compares it with the folder.
"""
import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

SKILLS = Path(__file__).resolve().parent.parent / "skills"


class BuildPyWithSkills(build_py):
    def run(self):
        super().run()
        if not SKILLS.is_dir():
            raise SystemExit("cannot find %s: build from a checkout of the repository" % SKILLS)
        target = Path(self.build_lib) / "abf_platform" / "skills"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(SKILLS, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


setup(cmdclass={"build_py": BuildPyWithSkills})
