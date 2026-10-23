# A shared terminal in the middle column, resume after a lost site without asking, one analysis per conversation

Amends ADR 0006 (the human channels), ADR 0009 (the three panes) and ADR 0010 (studio embedding).
Decided by the maintainer on 2026-10-23, in a design round held by the development lead on the
Artifact canvas (drafts V3-failed, V3-running, V3-terminal, V3-downstream-term, version 16), each
draft checked line by line against the maintainer's own words by a reviewer that had not seen the
lead's reasoning. Backend feasibility came from the backend development session the same day.
Everything not named here in ADR 0006, 0009 and 0010 stands.

## The problem this record answers

ADR 0009 put the progress of every analysis in the right column and a "Now" page at home; the
maintainer found the middle page redundant and the per-row "action" column strange. ADR 0006 asks a
person's yes before every write, including a resume after the site was lost for a few minutes,
which wakes the person for something they cannot decide differently. And the page had no terminal:
DESIGN.md v1 recorded "CLI terminal in the page: cancelled". The maintainer reversed that once it
was clear the AI's own commands could be shown there.

The maintainer's words (2026-10-22 and 10-23):

- 「狀態只要running, failed, successed就好，failed下面再去分原因……直接告訴使用者要做甚麼，不是讓他們選。"現在"的這個中間畫面有點多餘」
- 「我希望一個session處裡一條pipline，出問題非用者決定不可的問題了，ai直接告訴使用者要幹嘛。下載、看結果甚麼的點進去看就好了。」
- 「為甚麼沒看到之前設計過的，pipline裡面要有的launch, run, result等左右視窗?」
- 「分成四類 改成 跟Seqera platform一樣的模式，不要自己定義」
- 「是中欄有個可以切換主視窗跟終端機的按鈕。終端機能否直接使用? 我要在AI幫我跑時同時看到終端機的輸入指令變化，但我同時也可以自己打。下游的中欄主視窗是R studio，但切換成終端機就是跑在我的電腦。」
- 「國網連線斷掉時讓我直接在網頁終端機打密碼和一次性驗證碼（OTP）重新連上」
- 「直接續跑不用確認」 (resume after a lost site), and 「好的」 to a limit of one automatic resume per analysis.

## Decision

1. **Panes.** Left: the person's analyses grouped by project, each with its state (▶ ✗ ✓) and
   current stage; no "Now" page. Middle: the five-stage bar of ADR 0009 and the stage's content.
   Right: **this analysis's conversation** (one conversation per analysis). It speaks only when
   the person must act, in the formal-notice layout; automatic handling is recorded there as a
   "handled automatically" notice and never notifies.
2. **Three states**: Running, Succeeded, Failed. A lost run shows as Failed until it is resumed.
3. **Failures follow Seqera's model**, not a classification of our own: the run's `failure` field
   (Seqera status, the failed tasks as reported, the failure reason, and the actions Nextflow
   allows: resume and relaunch, or relaunch only). The notice shows one button, the first allowed
   action; the other stays in the run's menu.
4. **A shared terminal.** The middle column switches between the stage's main view and a
   terminal. In running it is a shell that reaches the site (NCHC or cloud); in downstream the
   main view is RStudio and the terminal runs on the person's own computer.
   - tmux and ttyd run on the machine of the station agent, never on NCHC; the shell reaches
     NCHC through the existing ssh master. NCHC needs tmux at most.
   - The station agent opens an outbound websocket to the platform; the platform joins the
     browser to it at `/term/<run id>`. Only the run's owner may open it, with a fresh sign-in
     each time; the websocket checks Origin; no token or PAT is in the shell's environment; an
     idle terminal closes; opening and closing are logged.
   - The AI reads the screen only (`tmux capture-pane`); it never types. A write the person
     confirmed (launch, cancel, resume, relaunch, package) is typed into the terminal by the
     station agent, from the confirmed job id, never from free text, so the person sees it run.
   - What the person types is not limited: the person is the human channel.
   - The terminal page is an exception to the web's no-JavaScript rule, like the studio embed.
5. **Passphrase and OTP through the page.** When the ssh master is gone, the person may type the
   passphrase and the one-time code into the web terminal. The platform relays those keystrokes
   and never stores, logs or echoes them.
6. **Resume after a lost site without a confirmation, once.** When a run is lost (no message for
   the lost threshold of `status.py`) and its site answers again, the platform submits one resume
   of the same confirmed launch, with the same bundle (`build.prepare_resume` already refuses a
   changed one). Only resume is automatic, never relaunch; at most once per analysis; a second
   loss becomes an "action needed" notice. The job records the original confirmation and the
   reason `site_lost`, so the record of who said yes stays true.

## Consequences for the constitution

Principle 2 and the Safety Net say every submission waits for a person's yes on a human channel,
and that the platform holds no site credential. Points 5 and 6 change both, so they are a MAJOR
amendment. Under the constitution's own rule an amendment joins with its check, so the amendment
text is written in the pull request that builds points 5 and 6 together with their tests: an
automatic resume happens only for a lost run, only once, only as resume, with the original
confirmation cited; relayed keystrokes never reach the database, the data folder or a log. Until
then both principles wait in `docs/ROADMAP.md`, "Principles waiting for a check".

## Not decided here

The exact lost threshold for an automatic resume (today's `status.py` value is the default), the
idle timeout of the terminal, and whether NCHC's login nodes allow a tmux session to live on.
