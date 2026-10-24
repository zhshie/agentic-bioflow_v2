# Opening an account for a colleague

This page is for the person who runs the platform (the operator) and for the colleague who is given an account. Every command below exists in the program; the test `platform/tests/test_onboarding_doc.py` checks that.

## 1. Who does what

中文要點：兩個角色，操作者開帳號，同事連線；國網同事另外在自己的電腦上裝站台代理，雲端用戶不用。

The **operator** runs the platform and opens accounts. The **colleague** is the person who gets an account and talks to the platform through an AI app.

| Who | Where | What |
|---|---|---|
| Operator | The platform host | Opens the account, sets the password, issues the PAT (the personal access token that lets the AI app in) |
| Colleague using the cloud | Their own computer | Connects the AI app (section 4). Google Batch runs are served by the station agent already running on the platform host, so they install nothing and there is no station agent on their side |
| Colleague using NCHC (the national HPC) | Their own computer, in WSL or Linux | Connects the AI app, and runs a station agent there (section 5) |

## 2. The operator opens the account

中文要點：管理者照順序做五步，每步一個指令；雲端月上限在開帳號時設，單位美元。

Run each command on the platform host. Replace the words in `<...>`.

1. Add the person, with the monthly cloud cap in US dollars:

```bash
abf-platform user add <name> --lab <lab> --cloud-cap-usd <N>
```

   Expected: the program confirms the user and tells you to issue a token. `<N>` is in US dollars, from 0 to 1,000,000. Without `--cloud-cap-usd` the person cannot send to the cloud until you set a cap later:

```bash
abf-platform user cloud-cap <name> <N>
```

   Expected: the new cap is shown. The person cannot change their own cap. NCHC runs have no cap.

2. Set the password the person logs into the confirmation page with:

```bash
abf-platform user passwd <name>
```

   Expected: it asks for the password twice. The person types it themselves in a real terminal; there is no flag and no file that can fill it in for them. If the person has no shell on the platform host, set it together at that host's terminal. (How a remote colleague should set it is still to be decided by the maintainer.)

3. Pick the way the person logs in. Claude Desktop needs only the web password from step 2 (OAuth, a login in the browser). Claude Code needs a PAT:

```bash
abf-platform pat new --user <name>
```

   Expected: the PAT is shown once. If it is lost, issue a new one. The person pastes it in their own terminal, never into a chat with the AI.

4. For a colleague on NCHC only, make a token for their station agent, then store the environment that agent serves:

```bash
abf-platform agent-token new <agent-name> --user <name>
```

   Expected: the agent token is shown once. Give it to the person to put in a file (section 5).

```bash
abf-platform ce create --owner <name> --agent <agent-name> ...
```

   Expected: the environment is stored. The other fields are in `docs/PLATFORM.md`, in the section on compute environments.

5. Check. Ask the person to follow section 5 of `docs/INSTALL.md`. On your side:

```bash
abf-platform pat list
```

   Expected: a line for the person's token. It never shows the value of a token.

## 3. The welcome message

中文要點：下面這一段可以原樣複製寄出，只要換掉四個佔位符。信裡沒有任何真實的 token、密碼、帳號或計畫號。

Copy this, replace `<platform-URL>`, `<name>`, `<lab>` and `<operator>`, and send it.

```text
Hi <name>,

Your account on the platform is ready (lab: <lab>).

Address: <platform-URL>

How you log in
- Claude Desktop: use your web password (set with me).
- Claude Code: I give you a PAT (a personal access token) separately. Paste it only in your own terminal, never into a chat.

Next steps
1. Follow docs/INSTALL.md to connect your AI app (section 4 of docs/ONBOARDING.md says how to check it works).
2. If you run on NCHC, also follow section 5 of docs/ONBOARDING.md on your own computer. You need your NCHC account and to be added to <your NSTC project> first.

Cloud cap: your monthly cloud spending cap is set by me, in US dollars. You cannot change it. Ask me if you need more.

If something does not work, look first in docs/INSTALL.md (section 5), then docs/ONBOARDING.md (section 2 is what I did on my side), then ask me.

<operator>
```

## 4. The colleague connects

中文要點：連線方法在 docs/INSTALL.md，這裡不重抄；連好後問一個唯讀的問題確認。

Follow `docs/INSTALL.md` for your AI app: its sections for Claude Code, Claude Desktop and Codex. The commands are not repeated here.

To check it works, ask the AI: "What is the state of my runs?" It calls `list_runs`, which only reads. An empty list is a correct answer when you have started nothing.

## 5. A colleague on NCHC runs a station agent

中文要點：國網同事在自己的電腦（WSL 或 Linux）上跑站台代理；不用在這裡教怎麼申請國網帳號。

You need three things first: an NCHC account, to be added to your project (`<your NSTC project>`), and WSL or Linux bash. The station agent refuses to start on native Windows or in Git Bash. Plain `http://` is only for the same machine: use https for every platform address except `localhost` and `127.0.0.1`.

Do these in order, in a WSL terminal. The order follows `docs/PLATFORM.md`.

1. Put the agent token the operator gave you in a file inside WSL's own home, not on a Windows drive such as `/mnt/c`:

```bash
mkdir -p ~/.config/abf
```

```bash
cat > ~/.config/abf/agent.token
```

   Paste the token, then press Ctrl-D.

2. Make the file readable by you only:

```bash
chmod 600 ~/.config/abf/agent.token
```

3. Open the shared connection to the site once, in this terminal. If none is open, this prints one line to paste:

```bash
bash scripts/on_site.sh --check-reach
```

   Run the line it prints yourself, and type the one-time code there. It keeps the connection for the day.

4. Start the station agent:

```bash
abf-station run --platform <platform-URL> --token-file ~/.config/abf/agent.token --deployment <root>
```

   `<root>` is the folder that holds `config/env.yaml`.

To see it is alive, ask the AI to call `list_agents`: your agent shows as `online`. If it does not start, the messages are explained in `docs/PLATFORM.md`, under "What it tells you".
