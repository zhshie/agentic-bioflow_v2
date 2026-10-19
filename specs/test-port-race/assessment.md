# test-port-race (bug, A tier)

Symptom: on CI, run_all runs platform pytest in 12 parallel shards and one test that starts a local server fails at random, a different one each run: test_confirm_page tcd18 (404 != 200), test_confirm_page tcd10 ('逾時' missing), test_oauth tca01_a02 (404 != 401); also once on feat/estimate-su. All pass locally. Seen on PRs #133 and #140 (docs-only).
Cause (from the log, to be confirmed): platform/tests/helpers.py free_port() binds port 0, reads the port, closes the socket and returns the number; the server under test binds it later. Between close and bind another shard's server can take the same port, so the test talks to a foreign server that answers 404 (time-of-check/time-of-use race).

## Fix

Make the port a test server listens on unique across concurrently running shards. Prefer the smallest change that removes the race, in order: (1) the child server binds port 0 itself and reports the port it got back to the test (if the server code already supports port 0 and prints its address, use that); or (2) a cross-process reservation: free_port() takes an exclusive lock file per port under a shared temp dir (fcntl/flock, held until the test's server is up or the test ends) and skips ports locked by another shard; or (3) after start, the helper verifies it is talking to its own server (e.g. a per-test random token the server echoes) and retries on a mismatch. Do not weaken any assertion, add sleeps as the fix, or skip tests. No production (non-test) code change unless option (1) needs a tiny, backwards-compatible one, which then needs its own test.

## Tests (write first)

A regression test that reproduces the race deterministically: two concurrent starts that would get the same port under the old free_port (e.g. monkeypatch to force the same candidate) must end with two servers on different ports, each test talking to its own. It must fail with the old helper.
Run the whole platform suite with the CI shard count locally (tests/platform_test.sh) at least twice: all green, 0 skipped.

## Out of scope

Any test assertion change, CHANGELOG.md, docs.
