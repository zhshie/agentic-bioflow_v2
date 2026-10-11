# Not Tower Agent: its wire protocol is undocumented and it talks only to Seqera; this agent speaks the three-request protocol of docs/PLATFORM.md and nothing else.
"""abf-station: the station agent. It runs on the user's side (WSL or Linux), connects outward to the
platform, takes read-only jobs, and answers them through the site script of this repository."""

__version__ = "0.1.0"
