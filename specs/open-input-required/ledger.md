# 畫布檢查：必填輸入沒接改成錯誤，可省略的仍是警告 progress ledger

- [x] `validate.py`: `OPEN_INPUT` is an error when the node has an incoming edge and a non-meta record of the channel has `optional: false`; otherwise a warning (裁決二). Message wording unchanged.
- [x] `test_validate.py`: `mod()` takes an optional 4th tuple item (no `optional` field by default); old open-input test renamed and rewritten to the new rule; new tests for TC-OI01..24.
- [x] `docs/PLATFORM.md` Validation: OPEN_INPUT sentence rewritten.
- expected.json files changed: 沒有. Hand check: `bad_edges` uses a synthetic catalogue with no `optional` field, so d's input 0 is not required, stays a warning. `good_fastqc_multiqc`: the only open input is fastqc input 0 on an entry node, so a warning. `open_inputs_twins`: s1 and s2 are entry nodes (no incoming edge), so all six stay warnings even though index_format is required.
