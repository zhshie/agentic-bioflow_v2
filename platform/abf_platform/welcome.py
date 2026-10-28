# Nothing existing: no mail or template library is wanted here; the letter is one fixed English text with five values filled in, kept identical to section 3 of docs/ONBOARDING.md.
"""The welcome letter of `abf-platform user welcome`: a pure function, no file, no network, no secret."""

_LETTER = """Hi <name>,

Your account on the platform is ready (lab: <lab>).

Address: <platform-URL>

How you log in
- Claude Desktop: use your web password. Either we set it together at the platform host's terminal, or I send you a temporary password separately; the first time you log in to the web page you must change it.
- Claude Code: I give you a PAT (a personal access token) separately. Paste it only in your own terminal, never into a chat.

Next steps
1. Follow docs/INSTALL.md to connect your AI app (section 4 of docs/ONBOARDING.md says how to check it works).
2. If you run on NCHC, also follow section 5 of docs/ONBOARDING.md on your own computer. You need your NCHC account and to be added to <your NSTC project> first.

<cap>

If something does not work, look first in docs/INSTALL.md (section 5), then docs/ONBOARDING.md (section 2 is what I did on my side), then ask me.

<operator>"""


def cap_sentence(limit):
    """The cloud cap line for this person: set and above 0, set to 0, or not set (None)."""
    if limit is None:
        return ("Cloud cap: I have not set your monthly cloud cap yet, so for now you cannot send runs to the cloud. "
                "NCHC runs are not affected.")
    if limit == 0:
        return "Cloud cap: your monthly cloud cap is US$0.00, so you cannot send runs to the cloud. Ask me if you need to."
    return ("Cloud cap: your monthly cloud spending cap is US$%.2f. It is set by me; you cannot change it. "
            "Ask me if you need more." % limit)


def welcome_text(name, lab, limit, platform_url, operator=None):
    """The letter with this person's name, lab, cap and the platform address; `<operator>` stays when no operator is given."""
    text = _LETTER.replace("<cap>", cap_sentence(limit))
    for key, value in (("<platform-URL>", platform_url), ("<name>", name), ("<lab>", lab), ("<operator>", operator)):
        if value:
            text = text.replace(key, value)
    return text
