# Fix plan: cd-target-backslash (issues #76, #75)

## Revision 3 (2026-10-10, after two acceptance REJECTs) — supersedes items 1–3 below where they conflict

Two rounds showed that modelling when the shell "really left" a directory keeps producing main-deny → branch-pass shapes (two slots cannot hold three candidates; conditions spanning lines; cmdlets that fail). New rule, chosen so that nothing can be looser than main by construction:

- The gate keeps a **set** of candidate directories (not two slots). Every relative target is judged against every candidate; the strictest verdict wins.
- Only what main already models replaces the set: `cd` / `pushd` to a literal target, exactly as main does today (main's own cd imprecision unchanged).
- Everything this PR adds can only **add** candidates, never remove one: the dropped-backslash copy of a segment, PowerShell location cmdlets (`Set-Location`/`sl`/`chdir`/`Push-Location`/`Pop-Location`, either tool, any form), and `popd` (any form, any context). A target the gate cannot read adds nothing and removes nothing.
- The pushd/popd stack, HIST_DIR, per-line suspicion and the exact-modelling rules of round 1 are removed; they are no longer needed.
- LISTER_OK from a copy may only tighten (item 4) and CW_HANDLED (item 5) stay.
- A relative `cd`/`pushd` target is resolved against **every** candidate (the set becomes {each candidate + target}); only an absolute target replaces the whole set (TC-045, TC-046).
- The set has a cap. When it is exceeded, harmless candidates are dropped first; the trunk (main's own VCWD) and every protected-looking candidate are always kept (TC-064, TC-065). Dropping extras can never be looser than main because the trunk stays.
- `popd`, `Pop-Location` and `dirs` add nothing and remove nothing, and the new handlers never `continue` past checks main already runs on those segments (TC-056, TC-066). The rclone remote-path branch clears the whole set and restores it afterwards (TC-063).
- Consequence accepted by the developer-agent: within one command, PowerShell-entering a protected folder and then leaving it still judges the protected folder (TC-027 becomes deny), and a bare `popd` back out of results is judged as main does (deny). These are over-asks/over-denies inside a single tool call, never under-protection.

# Revision 2 (after verifier CONTRACT review, 2026-10-10)

Tier A (Safety Net stricter). Touches `hooks/` → `/code-review` security pass before merge.
Governing rule for every item: nothing that main denies or asks may pass. Where the gate cannot tell which of two directories the shell is in, it judges both and the stricter verdict wins.

## What changes

1. **Two candidate directories.** `hooks/confirm_cleanup.sh` keeps VCWD_B next to VCWD: "another directory the shell may be in". Every relative target is judged against VCWD and, when VCWD_B differs, against VCWD_B too; stricter wins. All three resolution sites (judge_word ~700, find ~1190, mv sources ~1314) do this (TC-008, TC-009). The rclone remote-path save/clear/restore (~1065, `XCWD=$VCWD; VCWD=""`) saves, clears and restores VCWD_B as well.
   - A dropped-backslash copy segment (#74) updates VCWD_B only; #74's rule that a copy never changes VCWD stays (TC-037).
   - A plain directory change (cd/pushd/popd, or a PowerShell location cmdlet under the PowerShell tool) resolves its target against each candidate and sets both.
2. **PowerShell location cmdlets.** `Set-Location`, `sl`, `chdir`, `Push-Location`, `Pop-Location` (case-insensitive, TC-021). Target = first non-option word, or the value of `-Path` / `-LiteralPath`, including the colon-attached `-Path:X` / `-LiteralPath:X` form (TC-018..020). An unreadable target never counts as "moved somewhere harmless".
   - Under the PowerShell tool: they change directory like cd/pushd/popd (TC-014..016, TC-022..027).
   - Under the Bash tool (they are not built-ins there): Set-Location, sl, chdir, Push-Location update VCWD_B only, so the old directory is still judged (TC-035: `cd R/results; sl /tmp; rm -rf x` stays deny; TC-017: `Set-Location R/results; rm -rf x` becomes deny).
3. **A real directory stack** for pushd / Push-Location and popd / Pop-Location, kept for both views. `cd R/results; Push-Location /tmp; Pop-Location; Remove-Item -Recurse x` is judged in results → deny, as on main (TC-034, TC-036). A pop with an empty stack behaves exactly as main does today (pre-existing; issue #78).
4. **Lister verdict from a copy may only tighten.** After #74's restore of LISTER_OK, if the copy segment's own reading would set LISTER_OK=0 (a protected source), LISTER_OK becomes 0; a copy can never raise it. `Get-ChildItem res\ults | Move-Item -Destination x` asks like `Get-ChildItem results | ...` (TC-028..031; TC-032, TC-033 controls).
5. **Big-input prefilter.** `CW_HANDLED` (~765) gains set-location|sl|chdir|push-location|pop-location so the awk prefilter keeps those segments (TC-039); the here-doc awk-count assertion stays 3 (TC-040).

## Tests (RED first)

The verifier's `test-case.md` (TC-001..044) is the contract; every expectation is measured on main ("same command without the trick"). RED commit with the new cases failing, then GREEN. No existing case loosened (TC-038).

## Out of scope

- Variables, aliases, `$(...)` directory changes (TC-041..043 pin main's behaviour).
- `cd -`, bare `cd`, a pop with an empty stack, quoted `cd "res\ults"`: pre-existing, issue #78.
- Other hooks (TC-044).

## Done when

TC-001..044 pass; no existing case looser; CI green; verifier ACCEPT; `/code-review` finds no regression vs main.
