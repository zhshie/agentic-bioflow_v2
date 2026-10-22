# nano4 實機驗收：TC-047n～051n 與驗收表 progress ledger
- [x] acceptance-nano4: TESTING.md 'nano4 acceptance' (TC-047n-051n), specs/007b-launch/acceptance-nano4.md blank table, tests/docs_nano4_acceptance.sh (red then green).
- [x] fix round: TC-048n step 1 no longer says 'in Claude Desktop use estimate_su' (not an MCP tool); now a real python call to actions.estimate_su (checked it runs), with expected fields and unknown/not-found handling; table cell reworded. Open for maintainer: wire estimate_su as an MCP tool/command (separate task).
