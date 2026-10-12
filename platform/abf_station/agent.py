# Not Tower Agent or a Buildkite agent: those are bound to one vendor's service; this loop only says hello, polls, runs one built-in job at a time and answers.
"""The agent's loop: hello, then poll, run, answer.

It only ever calls the platform; nothing here accepts a connection. The two loops that exist are the
poll loop below and the beat that keeps the agent online while a job runs (a busy agent that stayed
silent would be shown as offline).
"""
import json
import signal
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from abf_platform import common

from . import __version__, handlers, launch
from .site import Site

LOOPBACK = ("127.0.0.1", "localhost", "::1")
EXIT_REJECTED = 3
BACKOFF = (2, 4, 8, 16, 30)


def say(text):
    print(text, flush=True)


class NetworkError(Exception):
    pass


class Terminated(SystemExit):
    pass


class Client:
    """One platform URL and one token. The token only ever goes into the Authorization header."""

    def __init__(self, url, token, name):
        self.base = url.rstrip("/")
        self.token = token
        self.name = name
        host = urllib.parse.urlparse(url).hostname or ""
        handlers_ = [urllib.request.ProxyHandler({})] if host in LOOPBACK else []
        self.opener = urllib.request.build_opener(*handlers_)

    def post(self, path, body, timeout):
        """(status, parsed JSON body). Raises NetworkError when no answer came."""
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.base + path, data=data, method="POST", headers={
            "Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=timeout) as resp:
                raw = resp.read()
                status = resp.status
        except urllib.error.HTTPError as e:
            raw, status = e.read(), e.code
        except (urllib.error.URLError, OSError, ValueError) as e:
            reason = getattr(e, "reason", e)
            raise NetworkError(str(reason)[:200])
        try:
            parsed = json.loads(raw) if raw else {}
        except ValueError:
            parsed = {}
        return status, parsed if isinstance(parsed, dict) else {}


class Beat(threading.Thread):
    """While a job runs: say hello every beat so the platform keeps showing the agent as online."""

    def __init__(self, client, interval, facts=None):
        super().__init__(name="beat")
        self.client = client
        self.interval = interval
        self.facts = facts
        self.stopping = threading.Event()

    def run(self):
        while not self.stopping.wait(self.interval):
            try:
                self.client.post("/agent/hello", {"name": self.client.name, "version": __version__,
                                                  "facts": self.facts() if self.facts else None}, timeout=5)
            except NetworkError:
                pass

    def finish(self):
        self.stopping.set()
        self.join(timeout=6)


class Rejected(Exception):
    pass


def _rejected(status):
    if status == 401:
        return ("the platform rejected the token (401): it is wrong or it was revoked. "
                "Ask for a new one with `abf-platform agent-token new <name>`.")
    return "the platform refused this agent (%d): the token was made for another agent name." % status


class Agent:
    def __init__(self, url, token, name, context):
        self.url = url
        self.client = Client(url, token, name)
        self.context = context
        self.heartbeat = common.heartbeat_seconds()
        self.poll = common.poll_seconds()
        self.failures = 0

    def wait_or_retry(self, why):
        delay = BACKOFF[min(self.failures, len(BACKOFF) - 1)]
        self.failures += 1
        say("cannot reach the platform at %s (%s); trying again in %d s" % (self.url, why, delay))
        time.sleep(delay)

    def hello(self):
        """Until the platform answers; a refusal stops the agent."""
        while True:
            try:
                status, body = self.client.post("/agent/hello", {"name": self.client.name, "version": __version__,
                                                                 "facts": launch.own_facts(self.context)}, 10)
            except NetworkError as e:
                self.wait_or_retry(str(e))
                continue
            if status in (401, 403):
                raise Rejected(_rejected(status))
            if status != 200:
                self.wait_or_retry("answered %d" % status)
                continue
            self.failures = 0
            for key, attr in (("heartbeat_seconds", "heartbeat"), ("poll_seconds", "poll")):
                v = body.get(key)
                if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                    setattr(self, attr, float(v))
            return body.get("agent") or self.client.name

    def answer(self, job_id, state, result):
        for attempt in range(3):
            try:
                status, _ = self.client.post("/agent/result/%s" % job_id,
                                             {"name": self.client.name, "state": state, "result": result}, 20)
            except NetworkError:
                time.sleep(1)
                continue
            if status in (401, 403):
                raise Rejected(_rejected(status))
            return

    def run_job(self, job):
        job_id = job.get("id") if isinstance(job, dict) else None
        if isinstance(job_id, bool) or not isinstance(job_id, int):
            say("a job without a usable id was ignored")
            return
        beat = Beat(self.client, self.heartbeat, lambda: launch.own_facts(self.context))
        beat.start()
        self.context.job_started = time.monotonic()
        self.context.agent_name = self.client.name
        try:
            state, result = handlers.handle(job, self.context)
        finally:
            beat.finish()
        say("job %d: %s" % (job_id, state))
        self.answer(job_id, state, result)

    def loop(self):
        name = self.hello()
        self.client.name = name
        say("abf-station %s is connected to %s as %s" % (__version__, self.url, name))
        while True:
            try:
                status, body = self.client.post("/agent/poll", {"name": name}, self.poll + 15)
            except NetworkError as e:
                self.wait_or_retry(str(e))
                continue
            if status in (401, 403):
                raise Rejected(_rejected(status))
            if status != 200:
                self.wait_or_retry("answered %d" % status)
                continue
            self.failures = 0
            job = body.get("job")
            if job is not None:
                self.run_job(job)


def _on_term(signum, frame):
    raise Terminated(143)


class Context:
    """What a handler may use: the site script and the deployment's settings file."""

    def __init__(self, site, settings_file, platform_url="", agent_name=""):
        self.site = site
        self.settings_file = str(settings_file)
        self.platform_url = platform_url
        self.agent_name = agent_name
        self.used_confirmations = set()    # confirmation ids this agent has run: a repeat is refused even if the platform repeats it
        self.job_started = time.monotonic()


def run(url, token, name, plugin_root, settings_file):
    """Run until told to stop. Returns the exit code."""
    agent = Agent(url, token, name, Context(Site(plugin_root, settings_file, log=say), settings_file, url, name))
    signal.signal(signal.SIGTERM, _on_term)
    try:
        agent.loop()
    except Rejected as e:
        say("abf-station stopped: %s" % e)
        return EXIT_REJECTED
    except Terminated as e:
        return e.code
    except KeyboardInterrupt:
        return 130
    return 0
