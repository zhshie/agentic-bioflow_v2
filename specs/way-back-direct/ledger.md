# 進度回報改走公開網址（way_back: direct） progress ledger
- [x] way-back-direct: own_facts reports way_back/platform_public_url; clean_facts whitelists them; _tower returns direct endpoint for way_back: direct (https or loopback), else refuses; forward untouched. Tests in test_station_channel.py.
- [x] fix round: TC-002 direct test now asserts no --check-forward/--unforward in ssh and site call records (the 7b24c1d loosening of the -O check assertion stays: -O check is the ssh reach check).
