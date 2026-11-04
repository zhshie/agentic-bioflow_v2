# CI 新增 gitleaks 與 pip-audit 掃描（獨立 workflow） progress ledger

- [x] .gitleaks.toml、platform/pip-audit-ignore.txt（cbf1cdaa）；security.yml（0ce2ca05，由 developer-agent 寫，因 .github/ 受寫入防護）；tests/ci_security_workflow_test.sh 12 項檢查全綠；docs/TESTING.md 新增「CI security checks」一節。
- tests.yml 未動。兩個 job 目前不是必過檢查（ruleset 未動）。方向題給維護者：觀察約兩週後是否設為必過？
- uses 釘版：actions/checkout 11bd7190...（v4.2.2）、actions/setup-python a26af69b...（v5.6.0）。executor 未以 GitHub API 重新查證（不 push、不連網）。
- 兩個 job 的首跑結果：未做（executor 不得 push）；由 lander／developer-agent 貼回此處。
