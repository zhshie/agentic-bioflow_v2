# ledger: acceptance-nano4-record

- [x] 步驟 1 紅：新複本還不存在時執行
  `bash tests/docs_nano4_acceptance.sh docs/TESTING.md specs/007b-launch/acceptance-nano4-2026-10-24-maintainer.md`
  輸出 `FAIL TC-012: specs/007b-launch/acceptance-nano4-2026-10-24-maintainer.md does not exist`，結束碼 1。
  不帶參數的 `bash tests/docs_nano4_acceptance.sh` 輸出 `ok`，結束碼 0。
- [x] 步驟 2 綠：新增 `specs/007b-launch/acceptance-nano4-2026-10-24-maintainer.md`；帶參數執行輸出 `ok`（結束碼 0），不帶參數輸出 `ok`（結束碼 0）
- [ ] 步驟 3：全套測試結果
- 備註（另案，本任務不動）：`docs/TESTING.md` TC-047n 第 4 點叫 `image_library`，空白表叫 `library`，名稱不一致；
  空白表檔頭寫「空格留空」，本次改寫「未記錄」，是否同步改檔頭另案裁決。
