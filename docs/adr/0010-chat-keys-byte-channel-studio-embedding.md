# Chat model keys, a byte channel, and the Studio screen: three gaps in the v3 web

Decided by the maintainer on 2026-10-17 (issue #118), on proposals written by the development lead. He accepted the proposed option for all three questions. The record below keeps the proposals as written, with the maintainer's answers in "Decided" at the end.

Amends: ADR 0004 (the chat's model), ADR 0009 (points 4 and 5). The wording changes it implies in `docs/PLATFORM.md` (sections 6 and 7) and `docs/ROADMAP.md` ("Principles waiting for a check") land with the feature that builds each part, not in this record.

## The problem this record answers

ADR 0009 promises three things the current design cannot deliver.

1. **The chat needs a model, and the platform may hold no credential.** ADR 0004 says the user brings their own API key or a local model. `docs/ROADMAP.md` lists "the platform stores metadata only and never holds a site credential". Section 7 of `docs/PLATFORM.md` refuses any field that looks like a key (an `AKIA` id, `aws_secret_access_key`, `export TOKEN=...`, a field named `password`, `token`, `secret` or `key`). A hosted chat page cannot reach a model on the user's own machine. The maintainer also agreed on 2026-10-17 (not yet in the repo) that the chat may use the platform's tools plus a vetted, read-only set of external tools (PubMed, nf-core documentation, SRA), and that a query sent to a third party must be disclosed.
2. **There is no way to move bytes.** The station agent speaks JSON over HTTPS long-polling and never accepts a connection (`specs/007-station-agent/research.md`, "Long-poll HTTPS, not WebSocket"; `docs/PLATFORM.md` section 6). `fetch-records` is capped at 20 MB per file. ADR 0009 needs an upload of up to about 2 GB, the rendered reports, the download of the finished package, and a Studio that sees a run's outputs.
3. **The Studio screen has no route into the page.** ADR 0009 point 4 says the Studio runs by default on the person's own computer and "its screen is shown inside the web page". The agent is outbound-only, so the platform cannot reach the Studio, and the page may be opened on another machine than the agent's.

## Decision proposals

### 1. Where the model key lives: in the browser, never on the platform

The key is typed into the settings of the web page and kept in that browser only (memory for the session, or `localStorage` if the person ticks "remember"). The page calls the model provider itself. When the model asks for a tool, the page calls the platform's MCP tools with the person's own login. The platform sees the tool calls, never the key and never the model's reply.

- The credential scanner is not loosened. It is extended to refuse model-key shapes (`sk-ant-...`, `sk-...`) in every field, so a key typed into the wrong place is refused by name.
- The page ships no third-party scripts and sets a strict Content-Security-Policy, because a script injected into the page could read the key. This is a stated residual risk, not a solved one.
- **External read-only tools** (PubMed, nf-core docs, SRA) are called by the platform on the page's behalf, from a fixed allow-list in the code, so the page needs no CORS access to those sites. Every such call shows "this query goes to <site>" in the chat before the first use per session, and the call is written to the run's audit line. The platform therefore sees the query text; it is disclosed, not hidden. A user-supplied MCP server stays out of v3.0.0 (as agreed).
- No key means no chat model. The rest of the stage board works, and rule-based fixes still run (ADR 0009 point 4).
- A local model (Ollama, LM Studio) is reached by the page at the person's own localhost; the person must allow the platform's origin in that program (for Ollama, the `OLLAMA_ORIGINS` setting). If the page is not on that computer, the chat says so.

Facts this rests on (read 2026-10-17):
- Anthropic's API accepts direct browser calls when the request carries the header `anthropic-dangerous-direct-browser-access: true`; it was added in August 2024, and its own author calls it fit only for "bring your own key" or trusted internal tools (https://simonwillison.net/2024/Aug/23/anthropic-dangerous-direct-browser-access).
- OpenAI's JavaScript SDK refuses to run in a browser unless `dangerouslyAllowBrowser` is set, because the key is then readable by anyone with the page (https://jsr.io/@openai/openai@6.49.0/doc/~/ClientOptions.dangerouslyAllowBrowser). Whether OpenAI's endpoints answer browser (CORS) requests reliably is NOT established: one forum thread reports an outage that removed the CORS headers and calls it a bug (https://community.openai.com/t/chat-completions-api-endpoint-down-blocked-any-web-browser-request/1362527). A spike must test each provider before it is listed as supported.

### 2. The byte channel: two paths, one rule that the platform never writes bytes to disk

Choose by where the browser is.

- **Path A, browser on the agent's machine.** The agent opens a listener bound to `127.0.0.1` only, with a one-time transfer token the platform issues per transfer. The page sends or fetches the bytes straight to it. The platform sees only the control messages ("transfer 7 started / done / checksum").
- **Path B, browser anywhere else.** The platform relays the stream, held in a bounded memory buffer and written nowhere. The browser sends 8 MiB chunks, each with a checksum, and the agent, over its own outbound HTTPS request, pulls the chunks as they arrive. A dropped connection resumes from the last acknowledged chunk. Both ends must be connected at once; if the agent is off, the page says so and nothing is stored.

What uses it:
- **Upload (up to about 2 GB):** the agent writes into the person's upload folder on the site only. This is the agent's first write path besides the confirmed launch, so it gets its own allow-listed job kind, a path allow-list under the project's upload folder, a size limit, and a human confirmation shown on the page (ADR 0006: the "yes" comes from a person).
- **Reports and package download:** the agent reads the file through `scripts/on_site.sh` and streams it out over path A or B. The 20 MB cap stays for `fetch-records`; it protects the platform's own records folder and is a different thing.
- **Studio mounts:** no platform channel is needed. The agent and the Studio are on the same computer, so the agent copies the run's outputs from the site to a local folder, and the Studio reads that folder.
- Anything over about 2 GB stays on `scripts/push.sh` from the person's machine, as ADR 0009 point 5 already says.

Costs and risks:
- Path A changes one sentence of `docs/PLATFORM.md` section 6 ("never accepts a connection"). It becomes: "never accepts a connection from the network; it listens on loopback only for a transfer the platform started, with a one-time token and an Origin check".
- A page served over HTTPS that talks to `localhost` may trigger a permission prompt in Chromium browsers since version 142 (the "Local Network Access" gate); a person who clicks Block breaks path A until they reset it (https://dynamsoft.com/web-twain/docs/faq/chromium-142-local-network-access-issue.html, https://developer.adobe.com/express/add-ons/docs/guides/getting-started/local-development/known-issues-limitations). The page must fall back to path B when path A is blocked.
- The public address in v3.0.0 is Tailscale Funnel. It listens only on ports 443, 8443 and 10000 and is "subject to non-configurable bandwidth limits"; the page does not state the figure (https://tailscale.com/kb/1223/funnel). A 2 GB relay through it is untested and may be slow or refused; the first spike measures it.

### 3. The Studio screen: an iframe of the agent's own localhost, with a new-tab fallback

The agent starts RStudio Server or Jupyter bound to `127.0.0.1:<port>` on its own machine and reports the address in its heartbeat. The page checks that this address answers from the browser:
- If it does, the page embeds it in an iframe, with a visible "open in a new tab" button.
- If it does not, the page says "your Studio runs on <machine name>; open this page there", and offers the person's other compute environments (as in ADR 0009 point 4).

The platform proxies no Studio traffic.

Facts and open checks (read 2026-10-17):
- Jupyter will only be embeddable if the server sends a `frame-ancestors` policy naming the platform's origin. Forum reports set it in `ServerApp.tornado_settings` (in `jupyter_server_config.py`) as a header; I found no official page for it, so the spike must confirm the key for the version we install (https://discourse.jupyter.org/t/csp-jupyterlab4/20917, https://discourse.jupyter.org/t/embed-jupyterlab-into-an-iframe/703). The same reports say kernels can fail with a 403 on the websocket or a cookie rejection when parent and Jupyter are on different origins, and that Chrome and Firefox differ (https://discourse.jupyter.org/t/websocket-issue-when-embedded-in-iframe/29868).
- The iframe tag needs the permission attributes Chrome's local-network gate asks for, or the frame is blocked (Adobe link above).
- Whether an HTTPS page may frame `http://localhost` without a mixed-content block is NOT confirmed by anything I found. The spike tests Chrome, Edge and Firefox.
- RStudio Server's open-source edition is AGPL-3.0; Posit sells Posit Workbench as the commercial server (https://support.posit.co/hc/en-us/articles/217801078-What-license-is-the-RStudio-IDE-available-under). Posit staff decline to give legal advice on corporate use (https://forum.posit.co/t/is-rstudio-open-source-edition-permitted-for-corporate-use/47191). We run the unmodified program on the user's own computer and do not redistribute it, which is the position stated in #118; a lawyer has not confirmed it. Jupyter is BSD per #118 (not re-checked).
- How RStudio Server logs a single local user in without a system account was not looked up; the spike settles it.

## Considered Options

### Question 1, the model key
- **A (proposed): key in the browser, the page calls the provider.** Keeps the credential rule and the scanner exactly as written; the platform costs nothing per chat; works with a local model on the same machine. Costs: the key is exposed to any script on the page; a provider that refuses browser calls cannot be used; a person on a shared computer must not tick "remember".
- **B: the platform stores the key encrypted and calls the provider.** Works for every provider, any device, and a server-side tool loop is simpler. Rejected: it breaks the ROADMAP principle and the scanner rule outright and makes the platform a target; it would need a MAJOR amendment of the principle, and a leak is the operator's incident. The ROADMAP row would have to be reworded from "any credential" to "site credentials" first.
- **C: the key lives on the station agent, which calls the model for the page.** Keeps the rule (the agent is on the user's side) and works with local models. Rejected for v3.0.0: every token of a streamed answer rides a long-poll round trip, and the chat dies when the agent is off, which is exactly when a person needs help.

### Question 2, the byte channel
- **A (proposed): loopback when the browser is on the agent's machine, otherwise a streaming relay through the platform with nothing written to disk.** No storage of user data on the platform (ADR 0004); no new service. Costs: two code paths; a new listener and a new write job on the agent; the relay needs both ends online.
- **B: a third-party object store with signed upload links.** Handles any size and survives either end being offline. Rejected: a new account and bill, user data leaves the person's own space, and "the platform keeps no copy" no longer describes the system.
- **C: raise the JSON cap and send base64.** Smallest change. Rejected: 2 GB becomes about 2.7 GB of text in memory on three parties, and long-polling cannot be resumed.

### Question 3, the Studio screen
- **A (proposed): iframe of the agent's localhost with a new-tab fallback.** The platform sees no Studio traffic and there is no port to open on any server. Costs: works only when the browser is on the agent's machine; iframe, cookie and websocket quirks per browser (above).
- **B: new tab only, no iframe.** Fewest moving parts and no framing policy to configure. It does not match ADR 0009 point 4 ("inside the web page"), so it needs the maintainer's yes; it is the fallback in A anyway.
- **C: the platform reverse-proxies the Studio through the agent.** Works from any machine. Rejected for v3.0.0: it needs a two-way websocket tunnel, which `research.md` chose not to build, it puts a whole IDE session through the public address and its bandwidth limits, and it widens the AGPL question.

## Consequences

- `docs/ROADMAP.md`, "Principles waiting for a check", gains a row: "the model key never reaches the platform; a test posts a model-key shape to every API route and web form and expects a refusal that names the field". Its check is the extended scanner, not a promise.
- `docs/PLATFORM.md` section 6 changes the "never accepts a connection" sentence and lists the new job kinds. Section 7's refusal list gains the model-key shapes.
- ADR 0009 points 4 and 5 gain one line each pointing here: the Studio is embedded when the browser is on the agent's machine; upload is relayed or local.
- The agent's allow-list grows by one write (upload into the project folder) and one read (stream a named file). Both are on the confirmation path of ADR 0006.
- Three spikes come before the code that depends on them, each with a written result: (1) browser calls to each model provider; (2) a 2 GB relay through Tailscale Funnel; (3) the iframe, cookie and websocket behaviour of Jupyter and RStudio on three browsers.
- Open and not decided here: the cap per transfer, the disclosure text for external tools, and who may run an external tool before a key is set.

Sources read 2026-10-17: https://simonwillison.net/2024/Aug/23/anthropic-dangerous-direct-browser-access, https://jsr.io/@openai/openai@6.49.0/doc/~/ClientOptions.dangerouslyAllowBrowser, https://tailscale.com/kb/1223/funnel, https://support.posit.co/hc/en-us/articles/217801078-What-license-is-the-RStudio-IDE-available-under, https://forum.posit.co/t/is-rstudio-open-source-edition-permitted-for-corporate-use/47191, https://discourse.jupyter.org/t/csp-jupyterlab4/20917, https://dynamsoft.com/web-twain/docs/faq/chromium-142-local-network-access-issue.html.

## Decided (maintainer, 2026-10-17)

1. **Model key:** option A. The key stays in the person's browser and the platform never sees it. External read-only tools (PubMed, nf-core docs, SRA) are called by the platform from a fixed allow-list, and each one is disclosed before its first use.
2. **Byte channel:** option A. Loopback when the browser is on the agent's machine, otherwise a relay through the platform that writes nothing to disk. The agent gets its first loopback listener and its first write (into the person's upload folder, each time confirmed by a person).
3. **Studio screen:** option A, with the new-tab button as the fallback. The three-browser spike comes first. If it fails, the Studio opens in a new tab.
4. **RStudio Server licence:** run the unmodified program on the person's own computer and do not bundle it. Ask a lawyer before charging another lab.

Answered in the same round (recorded here so the feature plans can cite one place):
- Accounts on the hosted service are created by the operator at a terminal. There is no self sign-up in v3.0.0.
- Every resume or relaunch needs a person's confirmation, the same as a first launch.
- No Studio on NCHC in v3.0.0. Studios run on the person's own computer or a cloud compute environment.
- The cloud cap per person per month is set when the account opens. Until then the page shows "—".
- Operator administration is the `abf-platform` command line in v3.0.0. A small admin page waits for a second lab.
- The demo the maintainer asked for is the real page built in slice 011a, not a mock-up.
