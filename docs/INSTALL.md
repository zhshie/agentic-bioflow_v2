# Connecting your AI app to the lab's abf platform

This is for a lab member whose lab already runs the abf platform. You add one MCP address
(an MCP server is how an AI app talks to the platform) and install nothing else. The first
three apps are Claude Code, Claude Desktop and Codex. Everything here is taken from
`docs/PLATFORM.md`, `docs/MIGRATION.md` and `docs/OPERATIONS.md`; where something is not
built, it says so.

## 1. What you need

- **The platform's address**, from the operator (the person who runs the platform). Below it
  is written `<platform-URL>`; the MCP door is `<platform-URL>/mcp`.
- **A way to prove who you are**, and it differs by app:
  - Claude Desktop uses an OAuth login in your browser (name and web password). You paste no
    token. The operator sets your web password with `abf-platform user passwd <name>`.
  - Claude Code (and any other client that takes a header) uses a personal access token,
    a PAT. The operator makes it with `abf-platform pat new` and gives it to you.
- A PAT is shown **once**. If you lose it, the operator issues another; it cannot be shown
  again. Type commands that contain a PAT in your own terminal. Never paste it into a chat
  with the AI, a file kept in git, or a params file. A PAT does not log you into the web page.

## 2. Claude Code

In your own terminal, with the address and PAT the operator gave you:

```bash
claude mcp add --transport http abf-platform <platform-URL>/mcp --header "Authorization: Bearer <PAT>"
```

The repository ships a Claude Code kit, `extensions/claude-code-kit/settings.json`. It puts
an `ask` permission rule on `launch`, `cancel`, `resume` and `relaunch`, so Claude Code asks
you before it calls them. That is a second layer, not the gate: the platform itself refuses
a launch or cancel until you press 送出 yourself (in the form your client shows, or on the
confirmation page). The PAT, the `ask` rule and a login click are never that confirmation.

## 3. Claude Desktop

1. In Claude Desktop add a custom connector.
2. Enter only the address `<platform-URL>/mcp`. No PAT, nothing to install.

Claude Desktop connects from the cloud, so the platform needs a public https address (the
operator starts it with `--public-url`). This path has not yet been tried end to end on a
real Claude Desktop; `docs/TESTING.md` lists the manual check still to be recorded.

What you see the first time you use the connector:

1. Your browser opens the platform's login page. You log in with your name and web password.
2. A consent page shows the connector's name, the host it will return to, and in plain words
   what it may do.
3. You press Allow or Deny. Deny refuses the connector. Consent is not remembered, so the
   page asks again each time the connector authorizes.

Allowing a connector is not agreeing to any launch. A launch or cancel still waits for your
own 送出. To end all your OAuth logins the operator runs `abf-platform oauth revoke <name>`.

## 4. Codex

Not built yet: the repository has no Codex kit, so there are no steps to give here. See
section 6.

## 5. Check it works

Ask the AI: "What is the state of my runs?" It calls `list_runs`, which only reads and starts
nothing. Over HTTP it lists only the runs you started through MCP. If you have started none,
the right answer is an empty list, `{"runs": []}`. That is correct, not a broken
connection. A refused connection shows as 401, meaning the platform did not accept your PAT
or login; ask the operator.

## 6. Not built yet

- A root `.mcp.json` that would add the platform with no command.
- A Codex kit (a root plugin.json and mcp.json).
- A Claude Desktop connector kit.
