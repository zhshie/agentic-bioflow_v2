# Nothing existing: the human side of launch and cancel (the question on the terminal, the hand-off listing); it is a package of its own so that abf_platform, the receiver, stays free of the agent's code and vocabulary.
"""abf_launch: the commands a person types to launch, cancel and follow an analysis (feature 007b).

abf_platform/cli.py registers them next to the older commands; this package holds their code. It may import both
abf_platform (the tables, the queue) and abf_station.launch (the one function that renders a launch), and the receiver
and the MCP server import neither it nor the confirmation module it uses.
"""
