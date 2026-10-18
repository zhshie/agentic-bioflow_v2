# testing-web: web test strategy in docs/TESTING.md

Source: issue #119 item 'Web test strategy'. Docs only, A tier.

## Goal
Add one section to `docs/TESTING.md` (do not rewrite the rest): 'Testing the web'.
- Half 1 (machine): the web is tested with Starlette TestClient asserting on the returned HTML (status code, key text, forms/links present); no browser-automation dependency (no Playwright/Selenium) - say why (one more heavy dependency, flaky on WSL/CI). Point to the real existing web tests under `platform/tests/` (grep for TestClient) as examples, by file name.
- The parity test (ROADMAP: every action has an MCP tool and a web route; owed list only shrinks) - say it arrives with 011a; if no file implements it yet on v3, say 'not built yet'.
- Half 2 (person): a manual procedure 'click-only 16S end to end': numbered steps setup -> launch -> running -> results -> finished done only by clicking in the web, what to check at each step, and what to record. Mark it as the procedure for Stage 3 (web 011-013) and that the pages it walks are not all built yet.

## Test (write first)
`tests/testing_web_doc_test.sh`:
- TESTING.md has the new heading and the words TestClient and 'click-only';
- the doc names no browser-automation package (playwright, selenium, puppeteer) except in the sentence saying they are not used - simplest: assert none of those names appears in `platform/pyproject.toml` / `platform/constraints.txt`;
- every `platform/tests/...py` file named in the new section exists.

## Out of scope
No code. Only the new section of docs/TESTING.md. Do not edit CHANGELOG.md.
