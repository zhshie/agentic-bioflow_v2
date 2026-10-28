# abf-platform user welcome：印出填好名字與雲端上限的歡迎信（不寄、不連網） progress ledger

- [x] RED: platform/tests/test_user_welcome.py（TC-001..TC-067 對應；實作前 31 紅／6 綠，綠的是守門員）
- [x] GREEN: platform/abf_platform/welcome.py（純函式 welcome_text）、cli.py 的 `user welcome` 接線、docs/ONBOARDING.md 第 2、3 節各加一句
- [x] 既有 test_onboarding_doc / test_cloud_cost / test_temp_password / test_scope 原樣綠（welcome.py 內不得出現 cap_usd 等字，test_cloud_cost 的「只有 store／cloud_cost／cli 知道上限」會抓）
