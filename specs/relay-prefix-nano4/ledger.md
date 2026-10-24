# 轉送程式的允許主機前綴改由設定讀入（nano4 範例） progress ledger

- [x] RED：test_relay_loopback.py（TC-001~077、088、064/065/068）、egress_ctl_restart_test.sh（TC-028/058/059）、nf_relay_domains_test.sh（TC-060）、on_site_test.sh（TC-054~057）
- [x] scripts/nf_relay.py：DEFAULT_HOST_PREFIXES、_parse_peer_prefixes、ALLOW_HOST_PREFIXES 由 NF_RELAY_PEER_PREFIXES 決定、startup_lines 新增 peers 行
- [x] scripts/egress_ctl.sh、scripts/on_site.sh：relay_peer_prefixes 帶進環境
- [x] docs/SETTINGS.md（新列＋Travels）、docs/SITE_ADAPTER.md（備援段）
- [ ] 全套測試在 HEAD 綠
