# Bug Assessment: two doc tests compare against the local ref `main` and silently skip without it

- **Slug**: doc-tests-local-main
- **Created**: 2026-10-10
- **Source**: issue #71 (Stage 0 acceptance review)
- **Verdict**: valid
- **Severity**: medium (a Safety Net check that never runs where it matters)

## 給維護者

1. 有兩個檢查要確認「安全網那段憲法一字沒改」和「詞彙表沒有刪掉舊詞」，做法是跟本機的 `main` 比。
2. GitHub 上的自動測試只抓最新一版、沒有 `main` 可比，於是印一行「略過」就算通過——等於在最需要它的地方從來沒跑。
3. 而且合併之後，`main` 就是改過的版本，自己跟自己比永遠一樣，也抓不到東西。
4. 修法：不跟 `main` 比，改跟寫死在測試裡的「標準答案」比（安全網那段的指紋、詞彙表的詞清單）。要改安全網，就得連標準答案一起改，在審查時一眼看得到。

## Where

- `tests/constitution_scope_test.sh:119-128`: the Safety Net section compared as a whole with `git show main:.specify/memory/constitution.md`; else "note: ... skipped".
- `tests/platform_direction_docs_test.sh:285-293` (TC-034): every bold term of `git show main:CONTEXT.md` must still be in CONTEXT.md; else "note: ... skipped".
- CI: `.github/workflows/*.yml` uses `actions/checkout@v4` with the default depth 1, so a PR run has no `main` ref.
- `tests/in_use_speed_test.sh` also reads main, but on purpose (timing against main's hook) and says so; out of scope.

## Root Cause

Both checks take their reference from a moving ref that is absent in CI and equal to the checkout after merge, and treat its absence as a pass.
