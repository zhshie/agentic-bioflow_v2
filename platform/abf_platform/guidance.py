# Not a skills-over-MCP SDK API: the pinned mcp 2.3.0 has none, so this reads the repo's one skills folder and the server serves it as plain prompts and resources.
"""The guidance that travels through the MCP URL (spec 009g): the routing table and the skill texts.

The text lives once, in the repository's skills/ folder. At build time that folder is copied into the
package as abf_platform/skills/ (platform/setup.py); this module reads whichever is there. It only reads;
it can start, cancel or write nothing.
"""
import re
from collections import namedtuple
from pathlib import Path

HEADING = "## The five commands"
PARAGRAPH_START = "**The user does not have to name a command.**"
MAX_BYTES = 2048

FIXED_SENTENCE = ("Seven tools of this server are read-only. Each of the tools launch, cancel, resume and relaunch only asks: it "
                  "does not start anything until the person says yes in their own client's form or on the page that the answer "
                  "names, and you cannot say it for them (in the terminal, abf-platform launch, cancel, resume and relaunch ask "
                  "the same way). A failed run is resumed or relaunched with its name alone. The tool forget only asks too: it "
                  "deletes nothing until the person says yes in their own client's form. The complete steps of each command "
                  "are the MCP prompt of the same name (setup, launch, runs, downstream, finish).")

SkillDoc = namedtuple("SkillDoc", "name description body_text")


class GuidanceError(Exception):
    """The skills folder is not what the server needs (a missing heading, table or file)."""


def skills_dir(package_dir=None):
    """The packaged copy abf_platform/skills/ if there is one, else the repository's skills/ folder."""
    package_dir = Path(package_dir) if package_dir is not None else Path(__file__).resolve().parent
    packaged = package_dir / "skills"
    if packaged.is_dir():
        return packaged
    return Path(__file__).resolve().parents[2] / "skills"


def skill_path(name, directory=None):
    return Path(directory if directory is not None else skills_dir()) / name / "SKILL.md"


def read_skill(name, directory=None):
    """The whole file, byte for byte, as text."""
    path = skill_path(name, directory)
    try:
        return path.read_bytes().decode("utf-8")
    except OSError as e:
        raise GuidanceError("cannot read %s: %s" % (path, e))


def _split(raw, where):
    if not raw.startswith("---\n"):
        raise GuidanceError("%s has no frontmatter" % where)
    end = raw.find("\n---\n", 3)
    if end < 0:
        raise GuidanceError("%s: the frontmatter is never closed" % where)
    return raw[4:end], raw[end + len("\n---\n"):]


def _field(frontmatter, key):
    m = re.search(r"^%s:[ \t]*(.*)$" % re.escape(key), frontmatter, re.M)
    return m.group(1).strip() if m else ""


def load_skills(directory=None):
    """{directory name: SkillDoc(name, description, body_text)} for every skills/<dir>/SKILL.md."""
    directory = Path(directory if directory is not None else skills_dir())
    out = {}
    for sub in sorted(p for p in directory.iterdir() if p.is_dir()):
        path = sub / "SKILL.md"
        if not path.is_file():
            continue
        frontmatter, body = _split(read_skill(sub.name, directory), str(path))
        out[sub.name] = SkillDoc(_field(frontmatter, "name"), _field(frontmatter, "description"), body)
    if not out:
        raise GuidanceError("no skills found in %s" % directory)
    return out


def routing_instructions(directory=None):
    """The MCP instructions: the operational skill's command table and routing paragraph, plus one fixed sentence."""
    raw = read_skill("operational", directory)
    start = raw.find("\n" + HEADING + "\n")
    if start < 0:
        raise GuidanceError("operational/SKILL.md has no '%s' heading" % HEADING)
    section = raw[start + len(HEADING) + 2:]
    nxt = section.find("\n## ")
    if nxt >= 0:
        section = section[:nxt]
    lines = section.split("\n")
    table, i = [], 0
    while i < len(lines) and not lines[i].startswith("|"):
        i += 1
    while i < len(lines) and lines[i].startswith("|"):
        table.append(lines[i])
        i += 1
    if len(table) < 3:
        raise GuidanceError("operational/SKILL.md has no command table under '%s'" % HEADING)
    at = section.find(PARAGRAPH_START)
    if at < 0:
        raise GuidanceError("operational/SKILL.md has no routing paragraph ('%s')" % PARAGRAPH_START)
    paragraph = section[at:].split("\n\n", 1)[0].strip()
    text = "\n\n".join(["Which command to reach for:", "\n".join(table), paragraph, FIXED_SENTENCE])
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise GuidanceError("the routing instructions are %d bytes, over the %d allowed"
                            % (len(text.encode("utf-8")), MAX_BYTES))
    return text
