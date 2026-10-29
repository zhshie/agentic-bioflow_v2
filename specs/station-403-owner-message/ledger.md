# 站台代理收到 403 時依平台訊息分辨名稱不符與擁有者不符 progress ledger

- RED (agent.py unchanged): `tests/test_station_rejected.py` 17 failed, 1 passed; all failures `TypeError: _rejected() takes 1 positional argument but 2 were given` (the signature does not yet accept the body).
- GREEN: 18 passed in test_station_rejected.py; 401 branch untouched; only agent.py + new test changed (plus specs).
