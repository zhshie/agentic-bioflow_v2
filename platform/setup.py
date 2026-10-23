# Not a pyproject-only setting: package-data cannot reach a folder outside platform/, so this build step copies the repository's one skills/ folder into the package.
"""Build hook for abf-platform (spec 009g): the wheel carries abf_platform/skills/ as a copy of <repo>/skills.

Everything else about the package is in pyproject.toml. The copy is made at build time and is never
committed (.gitignore); a test builds a wheel and compares it with the folder.
"""
import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"


class BuildPyWithSkills(build_py):
    def run(self):
        super().run()
        if not SKILLS.is_dir():
            raise SystemExit("cannot find %s: build from a checkout of the repository" % SKILLS)
        target = Path(self.build_lib) / "abf_platform" / "skills"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(SKILLS, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        # abf-station: scripts/ and configs/ go to abf_station/plugin/, shaped like the repo root, so a pip install needs no --plugin-root
        for name in ("scripts", "configs"):
            src = REPO / name
            if not src.is_dir():
                raise SystemExit("cannot find %s (the %s folder): build from a checkout of the repository" % (src, name))
            dest = Path(self.build_lib) / "abf_station" / "plugin" / name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        # the SU rates: one file in the repository, copied next to the other package data so abf_platform.su finds it after a pip install
        rates = REPO / "configs" / "sites" / "su_rates.json"
        if not rates.is_file():
            raise SystemExit("cannot find %s (the SU rates file): build from a checkout of the repository" % rates)
        data = Path(self.build_lib) / "abf_platform" / "data"
        data.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(rates, data / "su_rates.json")


setup(cmdclass={"build_py": BuildPyWithSkills})
