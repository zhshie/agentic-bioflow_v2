# abf-platform 說明清單補上 oauth、dataset、runs offer-cleanup progress ledger

- [x] RED (before editing line 2): 3 failed, 1 passed. Failures: top-level missing ['oauth','dataset']; nested missing ['oauth revoke','runs offer-cleanup','dataset register','dataset list','dataset show']; 'four commands' still present. Control test (core commands) green.
- [x] GREEN: cli.py line 2 rewritten (oauth revoke USER, runs assign|offer-cleanup, dataset register|list|show; hand-off sentence deleted, no count). 4 passed.
- Note: build_parser also registers launch, resume, relaunch, cancel, forget, launches, fetch-records (from abf_launch.cli.add_commands), so there are 19 top-level commands, not the 12 in the TC overview. Per ruling 1 the pointer sentence is deleted, so the tests exclude those commands (computed from abf_launch.cli.add_commands, with comment).
