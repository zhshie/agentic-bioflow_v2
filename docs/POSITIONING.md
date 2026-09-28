# 產品定位：競品比較、核心特點與目標客群

2026-09-28 經 `/grill-with-docs`（29 題）、兩次獨立審查（Fable）與一次硬體評估（Opus）後定案。
每個事實都附來源；**「推論」**標示的是判斷，不是來源說的。路線與階段見 `docs/ROADMAP.md`，
詞彙見 `CONTEXT.md`。本檔是給人看的商業文件，所以用中文。

## 一句話定位

> 沒有 HPC 也沒關係——用國網帳號或租一台雲端主機都行。學生用對話說出實驗目的，就能從原始資料一路做到可以發表的圖、表、文，AI 可以是你自己的，資料不離開實驗室。

## 核心特點

1. **Seqera 的基本功能，不必學一整個平台、不必買企業版。** 保留：連上 HPC／雲端主機、依管線自動產生參數（改成對話問）、樣本表、進度與失敗原因（讀 Nextflow 自己的紀錄）、從斷點續跑、看報告。不做：組織／工作區／七種角色、SSO、稽核、GxP、Data Explorer、Fusion、Studios（見 `docs/adr/0001`）。
2. **一條龍做到可發表的成果。** 管線跑完之後，用一般的 **Python／R 腳本**做統計與繪圖（依使用者目的與風格），最後一鍵打包圖、表、方法段與引用。腳本交給使用者，誰都能重跑。Seqera 在自家平台上最多做到 MultiQC 結果摘要〔來源：[Co-Scientist 產品頁](https://seqera.io/platform/co-scientist/)〕；Galaxy 的 Vintent 在瀏覽器裡產生圖〔來源：[Galaxy 26.0 發布說明](https://docs.galaxyproject.org/en/release_26.0/releases/26.0_announce_user.html)〕。
3. **在使用者自己的算力上跑、AI 可以是自己的。** 國網帳號或租的雲端主機，不必有人維護伺服器；雛形用 Claude，產品換成本地模型，資料不離開實驗室。
4. **跑的是 nf-core 標準管線**，審稿人認得；不是 agent 自己寫的新流程。
5. **使用者覺得是自己在分析**：每一步都看得到，腳本和參數都在使用者手上。

> 已排除的「特點」：「從實驗目的出發」——Seqera 的使用者一樣自己挑管線，不算差異（2026-09-28 他更正）。

## 護城河（推論）

程式碼開源後不是護城河。能慢慢長出來的只有三樣，而且目前都還沒有：

1. **台灣 HPC 實戰知識**：國網計算節點不能上網的繞法、QOS 資源下限、離線準備檔案——踩過坑才寫進 `docs/PITFALLS.md`。
2. **讓小模型跑得穩的經驗**：評測題庫（公開）、每次失敗的紀錄、為小模型調過的指令寫法（累積在手上）。
3. **在地關係與支援**：中文陪跑、台灣實驗室之間的口碑；國網可能是合作與推廣管道而不是對手。

獨立審查的提醒：差異化（對話式、自帶模型）Seqera 與 Galaxy 都在做，這些只是先發幾個月——這也是先當職涯作品集、有人付錢再轉創業的原因。

## 目標客群

| | 是誰 | 現況 | 為什麼選這個 |
|---|---|---|---|
| 付錢的人 | 大學農業、植病、微生物實驗室的 PI | 分析外包給定序公司或核心設施（台大生技中心每樣本 400–1,200 元〔來源：[cbt.ntu.edu.tw](https://www.cbt.ntu.edu.tw/service/service2)〕），或靠一個會寫程式的學生，畢業就斷 | 方法與腳本留在實驗室、資料不外流、比企業方案便宜 |
| 實際操作的人 | 研究生、專任助理 | 不會寫程式，看到終端機就退縮 | 用對話說出實驗目的就能做到論文圖表 |
| 第一批分析 | 16S 擴增子、RNA-seq | 最常見，nf-core 有成熟管線 | 自己有真實資料與圈內人脈 |
| 暫不做 | 醫院、頂尖癌症團隊 | 醫院有人體研究法、個資法特種資料；頂尖團隊有自己的生資人力或買得起企業方案 | 本地模型版成熟後再評估 |

## 競品比較

| 產品 | 使用方式 | 運算與資料在哪 | AI | 開源 | 收費 | 來源 |
|---|---|---|---|---|---|---|
| **Seqera Platform** | 網頁儀表板＋MCP | 客戶的雲／HPC，或 Seqera 代管 | Co-Scientist（有額度；自帶模型只限 Enterprise，且只支援 Claude） | Nextflow 開源、平台不開源 | 免費版 3 人、同時 3 個 run；其餘報價 | [pricing](https://seqera.io/pricing/)、[Co-Scientist 安裝](https://docs.seqera.io/platform-enterprise/enterprise/install-seqera-coscientist) |
| **Galaxy** | 網頁點選工具 | 公用站台或自架 | ChatGXY、Vintent（自然語言→圖） | ✅ | 公用站台免費 | [galaxyproject.org](https://galaxyproject.org/)、26.0 發布說明 |
| **Basepair** | 網頁＋CLI/API | 使用者自己的 AWS | 官網未提 | 查不到 | 按樣本或年約 | [basepairtech.com](https://www.basepairtech.com/) |
| **Terra** | 網頁＋Jupyter | Google Cloud | 查不到 | ✅ BSD-3 | Google Cloud 原價 | [terra.bio](https://terra.bio/) |
| **DNAnexus** | 網頁＋CLI | 平台雲或客戶雲 | 可部署 ML 模型 | 查不到 | 訂閱或按用量 | [dnanexus.com](https://www.dnanexus.com/) |
| **Latch Bio** | 網頁＋Python SDK | Latch 雲 | 主打生物 AI agent | 查不到 | 按用量 | [latch.bio](https://latch.bio/) |
| **EPI2ME** | 桌面程式 | 本機 | 查不到 | 流程開源 | 查不到；只做 Nanopore | [epi2me](https://epi2me.nanoporetech.com/) |
| **Biomni** | 網頁或 Python | 本機或其網站 | 本身是 agent，可接本地模型 | ✅ Apache（部分整合工具有商用限制） | 查不到 | [GitHub](https://github.com/snap-stanford/Biomni) |
| **BioMaster** | Python CLI | 本機，無 HPC 排程整合 | 本身是 agent，可接本地模型 | 無授權檔（等於保留所有權利） | — | [論文](https://pmc.ncbi.nlm.nih.gov/articles/PMC13494596/) |
| **FlowAgent** | CLI、網頁、MCP | 本機或 SLURM | 本身是 agent，可接本地模型 | GPL-3（併入會強制整個產品開源） | 免費 | [GitHub](https://github.com/EnteloBio/flowagent) |
| **國網 LIONS** | 帳號＋SSH 登入台灣杉 | 國網 HPC | 「GenAI × LIONS × HPC」細節查不到 | — | 國科會計畫 0.08 元/SU、學界 0.24 | [lions.nchc.org.tw](https://lions.nchc.org.tw/ngs.jsp) |

**跟我們最接近的兩家、各缺一塊（推論）**：Seqera Co-Scientist 自帶模型只限 Enterprise、只支援 Claude；Galaxy 有 AI 助理與自然語言畫圖，但要有人架站、跑的是 Galaxy 包裝過的工具而非 nf-core 標準管線。

## 可以直接用的零件

- ✅ Nextflow（Apache-2.0）、nf-core 管線與工具（MIT）、`tw`、tower-agent（Apache-2.0）、一般 R／Python 套件。
- ⚠️ Wave（AGPL-3.0，改過再對外提供服務要公開原始碼）；Fusion（即使不經 Platform 也要 Seqera 授權）——避開。
- ❌ 生資 agent 都不適合當零件：FlowAgent GPL-3；BioMaster、CellAgent 無授權檔；Biomni 可參考寫法，但它不跑 nf-core。「讓 AI 照步驟做事」這一層本來就是我們自己的核心。
- ❌ Jev（TypeSafe）：只能呼叫雲端付費 API（`api.typesafe.ai`），查不到自架版本，「不保留資料」只給企業客戶——跟「資料不離開實驗室」「不依賴別家」衝突〔來源：[docs.typesafe.ai/api](https://docs.typesafe.ai/api.md)、[legal](https://docs.typesafe.ai/legal.md)〕。

## 宿主（AI 外殼程式）與本地模型

結論：**本地模型套 Claude Code 只做實驗；產品的本地模型跑在 Codex 上。** 決策見 `docs/adr/0003`。

- Claude Code 技術上接得了本地模型（Ollama 的 Anthropic 相容層〔來源：[Ollama 文件](https://docs.ollama.com/api/anthropic-compatibility)〕），但 Anthropic 官方「不支援」〔來源：[llm-gateway](https://code.claude.com/docs/en/llm-gateway)〕，且它是「All rights reserved」授權，不能預裝在賣的主機裡〔來源：anthropics/claude-code LICENSE.md〕。
- Codex CLI（Apache-2.0）：`--oss` 接 Ollama／LM Studio；hook 事件與擋指令的寫法幾乎跟 Claude Code 相同；但不支援 `ask`（跳出確認）、對話紀錄路徑可能拿不到、只支援 `responses` 協定所以不能直接接 Claude〔來源：[hooks](https://learn.chatgpt.com/docs/hooks)、[config-reference](https://learn.chatgpt.com/docs/config-file/config-reference)〕。
- 現有 plugin 只有約 12% 是 Claude Code 專屬（主要是 `hooks/` 約 2,600 行＋plugin 設定檔），其餘可攜〔Fable 以 `wc -l` 實測〕。
- 在非 Claude Code 的宿主接 Claude，只能用 API key 按量付費：Anthropic 2026-02 起禁止把 Free／Pro／Max 訂閱用在其他工具〔來源：[The Register](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/)〕。

### 模型與電腦（實驗前的估計）

| | 模型 | 電腦 | M5 Pro 48GB |
|---|---|---|---|
| 最低能試 | Qwen3.6-35B-A3B（4-bit） | 48GB | ✅ 快 |
| 建議主力 | Qwen3.6-27B（Apache-2.0；SWE-bench Verified 77.2，Claude 4.5 Opus 80.9；建議至少 128K 上下文〔來源：[模型卡](https://huggingface.co/Qwen/Qwen3.6-27B)〕） | 64GB 以上較寬裕 | ✅ 慢 |
| 可能真正需要 | 70–120B+（gpt-oss-120b 等） | 128GB 級（DGX Spark、M5 Max 128GB） | ❌ |

- 唯一的生資 agent 論文說 30B 級「偶爾跑不完」「跨步驟一致性較常崩」，複雜長流程建議 70–120B+〔來源：[BioMaster 論文](https://pmc.ncbi.nlm.nih.gov/articles/PMC13494596/)〕——但它測的是舊版 Qwen3-30B，不是 3.6，所以要實驗才知道。
- 一次 16S launch 要同時放進約 39k token（CLAUDE.md＋SKILL＋launch.md＋ampliseq 參數定義），所以上下文至少 64k、最好 128k〔Opus 從 repo 實測，推論〕。
- Ollama 與 Qwen3.6 工具呼叫有未修的 bug（ollama issue #16383）；llama.cpp `--jinja` 實測較穩——實驗兩個引擎都要測。
- **這個答案決定主機成本**：30B 夠用 → 48–64GB 機器；要 120B → 128GB 級，價格約翻倍。

## 還不知道的

- 本地模型在 32k–128k 長上下文下的品質與速度（公開實測只到 4–8k）。
- 本地模型的統計正確性（沒有任何 benchmark 測過）。
- 替代役期間能否登記商業、收款（要問役政單位）；收費前 Seqera 條款怎麼解讀（問 Seqera 或律師）；nf-core 商標規範。
