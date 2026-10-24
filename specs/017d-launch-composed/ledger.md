# 畫布 017d：組合流程經同一確認流程送出 progress ledger

## 進度
- [x] module_sources + 資料檔（TC-066 至 083）：`module_sources.py`、`data/nf-core-module-sources.json.gz`、`pyproject.toml` 多一個 glob `data/*.json.gz`。

## 資料檔（TC-081、159；裁決 A、8）
- 來源：nf-core/modules @ 5ed90b42e78410e7411e9c6bdfeff33226d6c58e（shallow fetch 後用 `python -m abf_platform.module_sources snapshot` 產生）。
- 實際大小：766286 bytes（約 0.73 MiB），遠低於 8 MiB。
- 模組數 2116（與目錄快照逐一對上，沒有多也沒有少）；unsupported 3 個：`custom/addmostsevereconsequence`、`custom/addmostseverepli`（resources 底下有巢狀檔名 `resources/usr/bin/…`，形狀不符）、`last/dotplot`（main.nf 含 TC-072 形狀的叢集路徑，不改上游原檔所以整個標 unsupported）；其餘 2113 個可用。含 `include {` 或 `workflow ` 宣告的模組：0 個（對這份資料掃過）。
