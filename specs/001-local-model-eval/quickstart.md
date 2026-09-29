# Quickstart: 在你的 Mac 上跑一次評測

> 給維護者。第 4 段（S4）才用得到；前三段在 WSL 開發即可。

## 0. 準備（一次）

```bash
git clone https://github.com/zhshie/agentic-bioflow_v2 && cd agentic-bioflow_v2
brew install ollama llama.cpp r jq          # llama.cpp 用主線版本（research.md）
Rscript -e 'install.packages("BiocManager"); BiocManager::install(c("DESeq2","phyloseq"))'
ollama pull qwen3.6:35b-a3b                  # 其他候選同理；確切標籤於 S3 寫進 candidates/
```

## 1. 冒煙測試（S4 第一件事，各 1 次作答）

```bash
python3 scripts/eval/run_eval.py --candidate evals/local-model/candidates/claude.json --task t3-diagnose --trials 1
OLLAMA_CONTEXT_LENGTH=131072 ollama serve &
python3 scripts/eval/run_eval.py --candidate evals/local-model/candidates/qwen36-35b-a3b.ollama.json --task t3-diagnose --trials 1
```

要確認的三件事（research.md「plan 階段要先實測的」）：

1. 本地模型那次的紀錄顯示請求真的到了 Ollama（`record.json` 的 `engine_version` 有值、Ollama 日誌有對應請求）。不是 → 改用 `ABF_EVAL_RUNNER` 的 `claude -p` 備案。
2. 故意給一道會誘導送出分析的測試題時，紀錄是 `forbidden`，且沒有任何東西真的被送出。
3. 跑本地模型期間，除了 127.0.0.1 沒有其他對外連線（macOS：`nettop -p <claude 的 pid>` 觀察）。

## 2. 整晚評測

```bash
python3 scripts/eval/run_eval.py --candidate evals/local-model/candidates/qwen36-27b.llamacpp.json
python3 scripts/eval/run_eval.py --scorecard       # 早上看這份
```

## 3. 公開結果

```bash
python3 scripts/eval/run_eval.py --publish evals/local-model/results/2026-10-XX.md
```

只會寫出彙總表（沒有本機路徑、沒有原始作答），這份才可以 commit。
