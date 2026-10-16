Fixtures for tests/jev_test.sh (feature 015). JEV_DRY_RUN=<dir> makes
scripts/jev.sh read `<dir>/<sha256 of err_tail>.json`, else `<dir>/default.json`,
instead of calling the network. A fixture whose first line is `__timeout__`,
`__<http code>__` (for example `__500__`, `__429__`) or `__429_then_ok__`
(followed by the success body) simulates that failure. Nothing here is a key.
