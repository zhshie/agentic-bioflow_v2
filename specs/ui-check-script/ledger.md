# Ledger: ui-check-script (C8)

## Red run (tests/ui_check_script_test.sh before scripts/dev/ui_check.py and the .gitignore line existed)

```
FAIL --help exits 0 (got 2)
FAIL --help lists --base-url
FAIL --help lists --out
FAIL --help lists --pages
FAIL --help lists --start
FAIL .gitignore has ui-check-*/
ok   unknown option exits 2
ok   missing --base-url/--start exits 2
ok   unknown page name exits 2
FAIL no playwright exits 3 (got 2)
FAIL line names playwright
ui_check_script_test: FAIL
```
(The three "unknown option / missing / unknown page exits 2" lines were green only because a missing file also exits 2.)

## Real run

Command: `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers /tmp/abfv/bin/python scripts/dev/ui_check.py --start` (venv: playwright 1.63.0 pinned to match the preinstalled Chromium, because `playwright install chromium` could not download; axe-playwright-python 0.1.8). Exit code 1 (critical violations). Screenshots not committed.

### summary.md (full text)

Base: http://127.0.0.1:38879  |  2026-11-03 14:00

| page | width | lang | HTTP | critical | serious | moderate | minor |
|---|---|---|---|---|---|---|---|
| board | 1440 | zh | 200 | 1 | 0 | 1 | 0 |
| launch | 1440 | zh | 200 | 0 | 0 | 1 | 0 |
| settings | 1440 | zh | 200 | 0 | 0 | 1 | 0 |
| results | 1440 | zh | 200 | 1 | 0 | 1 | 0 |
| usage | 1440 | zh | 200 | 0 | 0 | 1 | 0 |
| board | 1440 | en | 200 | 1 | 0 | 1 | 0 |
| launch | 1440 | en | 200 | 0 | 0 | 1 | 0 |
| settings | 1440 | en | 200 | 0 | 0 | 1 | 0 |
| results | 1440 | en | 200 | 1 | 0 | 1 | 0 |
| usage | 1440 | en | 200 | 0 | 0 | 1 | 0 |
| board | 390 | zh | 200 | 1 | 0 | 1 | 0 |
| launch | 390 | zh | 200 | 0 | 0 | 1 | 0 |
| settings | 390 | zh | 200 | 0 | 0 | 1 | 0 |
| results | 390 | zh | 200 | 1 | 0 | 1 | 0 |
| usage | 390 | zh | 200 | 0 | 0 | 1 | 0 |
| board | 390 | en | 200 | 1 | 0 | 1 | 0 |
| launch | 390 | en | 200 | 0 | 0 | 1 | 0 |
| settings | 390 | en | 200 | 0 | 0 | 1 | 0 |
| results | 390 | en | 200 | 1 | 0 | 1 | 0 |
| usage | 390 | en | 200 | 0 | 0 | 1 | 0 |

## Serious / critical violations

- **critical** meta-refresh (1440, zh) - board - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (1440, zh) - results - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (1440, en) - board - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (1440, en) - results - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (390, zh) - board - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (390, zh) - results - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (390, en) - board - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (390, en) - results - 1 node(s), e.g. meta[http-equiv="refresh"]

## Screenshots (20)

- board-1440-zh.png
- launch-1440-zh.png
- settings-1440-zh.png
- results-1440-zh.png
- usage-1440-zh.png
- board-1440-en.png
- launch-1440-en.png
- settings-1440-en.png
- results-1440-en.png
- usage-1440-en.png
- board-390-zh.png
- launch-390-zh.png
- settings-390-zh.png
- results-390-zh.png
- usage-390-zh.png
- board-390-en.png
- launch-390-en.png
- settings-390-en.png
- results-390-en.png
- usage-390-en.png

