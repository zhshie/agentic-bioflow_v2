# Research: 評測工具（動手前先查，2026-09-29）

> 為 `/speckit-plan` 預先蒐集。每條事實附來源；「推論」標示的是判斷，不是來源說的。plan 階段需對其中標「待實測」的項目做冒煙測試（smoke test：最小規模試跑一次）。

## 決定（草案，plan 階段確認）

| 選項 | 決定 | 一句理由 |
|---|---|---|
| `claude plugin eval` 當執行器 | 採用 | 原生載入整包 plugin（skills、commands、hooks），每次 run 隔離，`--runs` 1–50，輸出 JSON〔來源：https://code.claude.com/docs/en/plugin-evals〕 |
| 自寫計分腳本 | 採用 | 內建評分器只有 `regex`、`tool_used`、`tool_order`、`file_exists`、`llm`、`baseline` 六種，沒有「跑腳本」，做不到數值容差與引用解析〔同上〕 |
| 內建 `llm` 評分器 | 不採用 | 規格 FR-004 禁止模型當評審；且（推論）評審可能也被導到本地模型 |
| 自寫 `claude -p` 迴圈 | 備案 | 可行（`--bare -p`、`--plugin-dir`、`stream-json` 的 `system/init` 列出 plugin 載入狀況）〔來源：https://code.claude.com/docs/en/headless〕，但隔離與準備資料要自己做 |
| Inspect AI | 暫不採用 | 重複與 pass@k 最完整〔來源：https://inspect.aisi.org.uk/reference/inspect_ai.scorer.html〕，但其 Claude Code 擴充能否載整包 plugin、能否接 Ollama 查不到 |
| promptfoo／DeepEval／OpenAI evals | 不採用 | 比 plugin eval 多一層卻不多給；OpenAI evals 不是為驅動 agent CLI 設計〔來源：各 GitHub repo〕 |
| LiteLLM／claude-code-router | 不需要 | Ollama 與 llama.cpp 都有原生 `/v1/messages` |

## 事實

- `claude plugin eval`：每次 run 開全新隔離的 `claude -p` 子行程；預設另跑一次不載 plugin 的對照，`--ablation none` 可關；`--keep-temp` 保留每次 run 的工作目錄；`--scaffold` 才會執行 `scaffold_script`；Bash 授權時套用 OS 層沙盒，原生 Windows 無沙盒後端要用 WSL2；分數是各 run 平均，不是逐次通過數〔來源：https://code.claude.com/docs/en/plugin-evals〕。
- 子行程繼承大部分 `ANTHROPIC_*`，文件未點名 `ANTHROPIC_BASE_URL`——**待實測**是否傳得進去〔同上〕。
- Anthropic 官方不支援經 gateway 把 Claude Code 接到非 Claude 模型〔來源：https://code.claude.com/docs/en/llm-gateway〕。
- Ollama：`ANTHROPIC_BASE_URL=http://localhost:11434`、`ANTHROPIC_AUTH_TOKEN=ollama`；不支援 `count_tokens`、prompt caching、tool-choice 控制、deferred tools〔來源：https://docs.ollama.com/api/anthropic-compatibility〕。
- llama.cpp：2026-01-19 起原生支援 `/v1/messages` 與 `count_tokens`，含 tool use 與串流〔來源：https://huggingface.co/blog/ggml-org/anthropic-messages-api-in-llamacpp〕。
- Ollama issue #16383（2026-06-01 開，仍 open）：Qwen3.6 偶爾偏離自己的工具呼叫格式，Ollama 0.24.0 解析器回 500；修補 PR #16398 仍 open〔來源：https://github.com/ollama/ollama/issues/16383、https://github.com/ollama/ollama/pull/16398〕。
- 主線 llama.cpp 以自動偵測正確解析該格式（第三方分支 issue 中的陳述）〔來源：https://github.com/TheTom/llama-cpp-turboquant/issues/199〕；主線本身的 Qwen3.6 bug 紀錄查不到。

## plan 階段要先實測的

1. `ANTHROPIC_BASE_URL` 是否傳進 plugin eval 子行程（不行就走備案迴圈）。
2. plugin 的 hooks 在 eval 沙盒外執行時，`confirm_launch` 是否仍攔得住 launch（FR-008）。
3. Mac 上的沙盒行為（文件只提原生 Windows 無後端）。
