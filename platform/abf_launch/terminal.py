# Not `click.confirm` or `input()`: they read whatever stdin is, so a pipe or a program can answer; this reads only a terminal that is the controlling terminal, and it shows nothing that is not escaped.
"""The screen and the question (feature 007b, FR-001).

A launch or a cancel is sent only after a person typed y or Y on the terminal this program runs in. Nothing else
answers: not a pipe, not a closed input, not a program without a controlling terminal, not a flag, not an environment
variable (there is none to look for). Everything on the screen goes through `esc`, which makes every control character
visible, and every line carries a prefix, so no value can hide a line of the screen or rewrite it.
"""
import os
import sys
import unicodedata

PREFIX = "| "
BIDI = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A)) | {0x200E, 0x200F, 0x061C}


def esc(text):
    """Text with every character that a terminal could act on, or that could hide something, written out visibly."""
    out = []
    for ch in str(text):
        o = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif o < 0x20 or o == 0x7F or 0x80 <= o <= 0x9F:
            out.append("\\x%02x" % o)
        elif o in (0x2028, 0x2029) or o in BIDI or unicodedata.category(ch) in ("Cf", "Cs", "Co", "Cn"):
            out.append("\\u%04x" % o if o <= 0xFFFF else "\\U%08x" % o)
        else:
            out.append(ch)
    return "".join(out)


def block(title, text):
    """A titled section: one prefixed line per line of text, each escaped on its own."""
    lines = [PREFIX + "== %s ==" % title]
    body = text.split("\n")
    if body and body[-1] == "":
        body.pop()
    lines += [PREFIX + esc(ln) for ln in body]
    return lines


def pair(label, value):
    return PREFIX + "%s: %s" % (label, esc(value))


def terminal_problem():
    """Why the answer cannot be taken from a person, or None. Input and output must be the terminal the program
    belongs to; a program that merely has a terminal as its input, but none as its controlling terminal, is refused."""
    if not (os.isatty(0) and os.isatty(1)):
        return "輸入或輸出不是終端機"
    try:
        os.close(os.open("/dev/tty", os.O_RDWR))
    except OSError:
        return "這個程式沒有控制終端機"
    try:  # Linux: the controlling terminal of this process, from /proc, must be the device standard input is
        with open("/proc/self/stat", encoding="ascii") as f:
            tty_nr = int(f.read().rsplit(")", 1)[1].split()[4])
    except (OSError, ValueError, IndexError):
        return None  # no /proc (macOS): opening /dev/tty above is the check that can be made
    major, minor = (tty_nr >> 8) & 0xFFF, (tty_nr & 0xFF) | ((tty_nr >> 12) & 0xFFF00)
    st = os.fstat(0).st_rdev
    if (os.major(st), os.minor(st)) != (major, minor):
        return "輸入不是這個程式的控制終端機"
    return None


def ask(lines, question):
    """Show the lines, ask the question on the terminal, and return True only for y or Y. The caller has already
    checked terminal_problem(). Ctrl-C, Ctrl-D and a closed terminal are 'no'."""
    out = sys.stdout
    out.write("\n".join(lines) + "\n" + question)
    out.flush()
    try:
        answer = sys.stdin.readline()
    except (KeyboardInterrupt, EOFError, OSError, ValueError):
        out.write("\n")
        return False
    if answer == "":
        out.write("\n")
        return False
    return answer.rstrip("\n") in ("y", "Y")
