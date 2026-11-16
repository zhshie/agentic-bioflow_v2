# downstream-method-catalog 進度

- [x] 目錄檔、schema 檢查、list_downstream（actions + MCP）、檢查腳本、文件、既有測試的名單與計數更新

## 轉換補註記（種子檔→目錄檔，未編造任何值）
- ampliseq-phyloseq: non_interactive_plot null，notes 補『待驗證』
- ampliseq-mia-miaviz-oma: non_interactive_plot null，notes 補『待驗證』
- ampliseq-ancom-bc: non_interactive_plot null，notes 補『待驗證』
- ampliseq-aldex2: non_interactive_plot null，notes 補『待驗證』
- ampliseq-microeco: non_interactive_plot null，notes 補『待驗證』
- ampliseq-maaslin2: non_interactive_plot null，notes 補『待驗證』
- ampliseq-vegan: non_interactive_plot null，notes 補『待驗證』
- rnaseq-differentialabundance: notes 補『pipeline_version 查不到』
- rnaseq-deseq2: notes 補『pipeline_version 查不到』
- rnaseq-edger: notes 補『pipeline_version 查不到』
- rnaseq-limma: notes 補『pipeline_version 查不到』
- rnaseq-clusterprofiler: inputs 清空，notes 補『待驗證』並附描述原文
- rnaseq-clusterprofiler: notes 補『pipeline_version 查不到』
- rnaseq-fgsea: inputs 清空，notes 補『待驗證』並附描述原文
- rnaseq-fgsea: notes 補『pipeline_version 查不到』
- rnaseq-tximport: notes 補『pipeline_version 查不到』
- rnaseq-tximeta: 種子檔有 tximeta，依裁決未收
- rnaseq-pcaexplorer: notes 補『pipeline_version 查不到』
- rnaseq-isee: notes 補『pipeline_version 查不到』
- rnaseq-debrowser: notes 補『pipeline_version 查不到』

## 每筆來源網址
- ampliseq-summary-report: https://nf-co.re/ampliseq/3.1.0/docs/output/; https://api.github.com/repos/nf-core/ampliseq; https://api.github.com/repos/nf-core/ampliseq/releases; https://raw.githubusercontent.com/nf-core/ampliseq/3.1.0/modules/local/summary_report/main.nf; https://raw.githubusercontent.com/nf-core/ampliseq/3.1.0/README.md; https://api.crossref.org/works/10.3389/fmicb.2020.550420; https://api.github.com/repos/nf-core/ampliseq/issues/1081
- ampliseq-ancombc: https://nf-co.re/ampliseq/3.1.0/docs/output/; https://api.github.com/repos/nf-core/ampliseq; https://raw.githubusercontent.com/nf-core/ampliseq/3.1.0/modules/local/qiime2_ancombc_tax/main.nf; https://api.crossref.org/works/10.1038/s41467-020-17041-7
- ampliseq-phyloseq: https://bioconductor.org/packages/release/bioc/html/phyloseq.html; https://api.github.com/repos/joey711/phyloseq; https://nf-co.re/ampliseq/3.1.0/docs/output/; https://raw.githubusercontent.com/nf-core/ampliseq/3.1.0/modules/local/phyloseq/main.nf; https://api.crossref.org/works/10.1371/journal.pone.0061217
- ampliseq-mia-miaviz-oma: https://bioconductor.org/packages/release/bioc/html/mia.html; https://bioconductor.org/packages/release/bioc/html/miaViz.html; https://api.github.com/repos/microbiome/mia; https://api.github.com/repos/microbiome/miaViz; https://api.github.com/repos/microbiome/OMA; https://nf-co.re/ampliseq/3.1.0/docs/output/; https://api.crossref.org/works/10.12688/f1000research.26669.2; https://api.crossref.org/works?rows=3&query.bibliographic=Orchestrating+Microbiome+Analysis+with+Bioconductor
- ampliseq-ancom-bc: https://bioconductor.org/packages/release/bioc/html/ANCOMBC.html; https://api.github.com/repos/FrederickHuangLin/ANCOMBC; https://nf-co.re/ampliseq/3.1.0/docs/output/; https://api.crossref.org/works/10.1038/s41467-020-17041-7; https://api.crossref.org/works/10.1038/s41592-023-02092-7
- ampliseq-aldex2: https://bioconductor.org/packages/release/bioc/html/ALDEx2.html; https://api.github.com/repos/ggloor/ALDEx_bioc; https://raw.githubusercontent.com/ggloor/ALDEx_bioc/master/DESCRIPTION; https://nf-co.re/ampliseq/3.1.0/docs/output/; https://api.crossref.org/works/10.1186/2049-2618-2-15
- ampliseq-microeco: https://api.github.com/repos/ChiLiubio/microeco; https://cran.r-project.org/web/packages/microeco/index.html; https://api.github.com/repos/ChiLiubio/microeco/releases/latest; https://api.crossref.org/works/10.1093/femsec/fiaa255
- ampliseq-maaslin2: https://bioconductor.org/packages/release/bioc/html/Maaslin2.html; https://api.github.com/repos/biobakery/Maaslin2; https://raw.githubusercontent.com/biobakery/Maaslin2/master/DESCRIPTION; https://api.crossref.org/works/10.1371/journal.pcbi.1009442
- ampliseq-vegan: https://cran.r-project.org/web/packages/vegan/index.html; https://api.github.com/repos/vegandevs/vegan; https://api.github.com/repos/vegandevs/vegan/releases/latest; https://nf-co.re/ampliseq/3.1.0/docs/output/
- rnaseq-differentialabundance: https://api.github.com/repos/nf-core/differentialabundance; https://api.github.com/repos/nf-core/differentialabundance/releases/latest; https://nf-co.re/differentialabundance/2.0.0/docs/usage; https://nf-co.re/differentialabundance/2.0.0/docs/output; https://raw.githubusercontent.com/nf-core/differentialabundance/2.0.0/README.md
- rnaseq-deseq2: https://bioconductor.org/packages/release/bioc/html/DESeq2.html; https://api.github.com/repos/thelovelab/DESeq2; https://bioconductor.org/about/release-announcements/; https://api.crossref.org/works?query.bibliographic=DESeq2
- rnaseq-edger: https://bioconductor.org/packages/release/bioc/html/edgeR.html; https://bioconductor.org/about/release-announcements/; https://api.crossref.org/works?query.bibliographic=edgeR
- rnaseq-limma: https://bioconductor.org/packages/release/bioc/html/limma.html; https://bioconductor.org/about/release-announcements/; https://nf-co.re/differentialabundance/2.0.0/docs/usage; https://api.crossref.org/works?query.bibliographic=limma
- rnaseq-clusterprofiler: https://bioconductor.org/packages/release/bioc/html/clusterProfiler.html; https://api.github.com/repos/YuLab-SMU/clusterProfiler; https://bioconductor.org/about/release-announcements/; https://api.crossref.org/works?query.bibliographic=clusterProfiler
- rnaseq-fgsea: https://bioconductor.org/packages/release/bioc/html/fgsea.html; https://api.github.com/repos/alserglab/fgsea; https://bioconductor.org/about/release-announcements/; https://api.crossref.org/works?query.bibliographic=Fast+gene+set+enrichment+analysis
- rnaseq-tximport: https://bioconductor.org/packages/release/bioc/html/tximport.html; https://api.github.com/repos/thelovelab/tximport; https://nf-co.re/rnaseq/3.27.0/docs/output; https://bioconductor.org/about/release-announcements/; https://api.crossref.org/works?query.bibliographic=tximport
- rnaseq-pcaexplorer: https://bioconductor.org/packages/release/bioc/html/pcaExplorer.html; https://api.github.com/repos/federicomarini/pcaExplorer; https://nf-co.re/rnaseq/3.27.0/docs/output; https://bioconductor.org/about/release-announcements/; https://api.crossref.org/works?query.bibliographic=pcaExplorer
- rnaseq-isee: https://bioconductor.org/packages/release/bioc/html/iSEE.html; https://api.github.com/repos/iSEE/iSEE; https://nf-co.re/rnaseq/3.27.0/docs/output; https://bioconductor.org/about/release-announcements/; https://api.crossref.org/works?query.bibliographic=iSEE
- rnaseq-debrowser: https://api.github.com/repos/UMMS-Biocore/debrowser; https://bioconductor.org/packages/release/bioc/html/DEBrowser.html; https://nf-co.re/rnaseq/3.27.0/docs/output; https://api.crossref.org/works?query.bibliographic=DEBrowser

## 裁決與取捨
- 種子檔有 tximeta，依裁決未收（共 19 筆：ampliseq 9、rnaseq 10）。
- vegan 與 MaAsLin2 維持 B（種子檔與計畫的分級有出入，依 lead 裁決不升）；DEBrowser 為 B，其餘 rnaseq 為 A。
- 時效界線：審查日距今「大於 365 天」才降一級；剛好 365 天不降（TC-Q04）。
- chat_tools.CHAT_SYSTEM_PROMPT 加了一行，只提 list_downstream 這個工具名，沒有任何方法名（TC-M10 測試把關）。
- 錯誤訊息：空 pipeline 在 catalogue 層丟 ValueError；MCP 層用 `_plain_errors` 裝飾器轉成 ToolError（不進 tool 函式本體，本體仍是單一呼叫），不外洩堆疊或路徑。actions/downstream.py 維持只用標準函式庫。
- 計畫的數字過時：計畫寫 22 個工具／15 唯讀，實際基底是 26／16，完成後 27／17。所有釘住 26／16 或名單的既有測試只改計數與名單（加入 list_downstream），沒有放寬任何斷言；快照 tools.json 以 ABF_UPDATE_MCP_SNAPSHOT=1 重生，只多 list_downstream。
- 不需要 migration：目錄是隨程式出貨的 JSON，沒碰 store.py。

## 改動的既有測試（只動計數／名單）
test_actions_layer, test_aws_launch/ce, test_azure_launch/ce/upload, test_gcb_launch/ce, test_k8s_ce, test_estimate_su, test_su_in_get_run, test_su_usd, test_pat, test_oauth_mcp, test_mcp, test_mcp_launch_pipeline, test_mcp_run_file, test_mcp_server_doc, test_publish_figure_confirm, test_dataset_launch, test_human_channel, test_keep_submissions, test_launch_e2e/platform/profiles, test_resume_*, test_chat_confirm, test_chat_tools, test_guidance, test_station_envs/launch, test_owner_guard, test_http_site_samplesheet, test_web_board, test_web_guided_launch_preview, mcp/test_mcp_contract_tools/writes, tests/platform_storage_doc_test.sh（錨點 Twenty-seven tools.）。

## git diff --stat
`git diff --stat origin/v3...HEAD`（本次收尾 commit 之前的四個 commit；收尾 commit 另改 9 個測試檔、ledger 與 decisions.tsv）：

```
 docs/PLATFORM.md                                   |   6 +-
 platform/abf_platform/actions/chat_tools.py        |   1 +
 platform/abf_platform/actions/downstream.py        |  10 +
 platform/abf_platform/data/downstream-methods.json | 450 +++++++++++++++++++++
 platform/abf_platform/downstream_catalog.py        | 143 +++++++
 platform/abf_platform/mcp_server.py                |  38 +-
 platform/tests/mcp/snapshots/tools.json            |  17 +
 platform/tests/mcp/test_mcp_contract_tools.py      |   2 +-
 platform/tests/mcp/test_mcp_contract_writes.py     |   3 +-
 platform/tests/test_actions_layer.py               |  12 +-
 platform/tests/test_aws_ce.py                      |   2 +-
 platform/tests/test_aws_launch.py                  |   4 +-
 platform/tests/test_azure_ce.py                    |   2 +-
 platform/tests/test_azure_launch.py                |   4 +-
 platform/tests/test_azure_upload.py                |   2 +-
 platform/tests/test_chat_confirm.py                |   2 +-
 platform/tests/test_chat_tools.py                  |   2 +-
 platform/tests/test_dataset_launch.py              |   2 +-
 platform/tests/test_downstream_catalog.py          | 369 +++++++++++++++++
 platform/tests/test_estimate_su.py                 |   2 +-
 platform/tests/test_gcb_ce.py                      |   2 +-
 platform/tests/test_gcb_launch.py                  |   4 +-
 platform/tests/test_guidance.py                    |   2 +-
 platform/tests/test_http_site_samplesheet.py       |   2 +-
 platform/tests/test_human_channel.py               |   2 +-
 platform/tests/test_k8s_ce.py                      |   2 +-
 platform/tests/test_keep_submissions.py            |   2 +-
 platform/tests/test_launch_e2e.py                  |   2 +-
 platform/tests/test_launch_platform.py             |   2 +-
 platform/tests/test_launch_profiles.py             |   2 +-
 platform/tests/test_mcp.py                         |   4 +-
 platform/tests/test_mcp_launch_pipeline.py         |   2 +-
 platform/tests/test_mcp_list_downstream.py         | 112 +++++
 platform/tests/test_mcp_run_file.py                |   4 +-
 platform/tests/test_mcp_server_doc.py              |  10 +-
 platform/tests/test_oauth_mcp.py                   |   4 +-
 platform/tests/test_owner_guard.py                 |   2 +-
 platform/tests/test_pat.py                         |   8 +-
 platform/tests/test_publish_figure_confirm.py      |   2 +-
 platform/tests/test_resume_edit_params_platform.py |   2 +-
 platform/tests/test_resume_entrypoints.py          |   2 +-
 platform/tests/test_station_envs.py                |   2 +-
 platform/tests/test_station_launch.py              |   2 +-
 platform/tests/test_su_in_get_run.py               |   2 +-
 platform/tests/test_su_usd.py                      |   2 +-
 platform/tests/test_web_board.py                   |   2 +-
 platform/tests/test_web_guided_launch_preview.py   |   2 +-
 scripts/check_downstream_catalog.py                |  65 +++
 specs/downstream-method-catalog/decisions.tsv      |   5 +
 specs/downstream-method-catalog/ledger.md          |  61 +++
 specs/downstream-method-catalog/test-case.md       | 179 ++++++++
 tests/platform_storage_doc_test.sh                 |   2 +-
 52 files changed, 1511 insertions(+), 60 deletions(-)
```

## git grep（漏掃防線，行截到 200 字元）
`git grep -n -E '== 22|== 15|"describe_module"|fifteen|Fifteen|Twenty-two' origin/v3 -- platform/tests tests docs/PLATFORM.md`（57 行）：

```
origin/v3:platform/tests/mcp/snapshots/tools.json:91:    "name": "describe_module"
origin/v3:platform/tests/mcp/test_mcp_contract_tools.py:18:    "my_usage", "run_outputs", "read_run_file", "list_figures", "read_task_log", "find_module", "describe_module", "list_pipelines",
origin/v3:platform/tests/mcp/test_mcp_contract_writes.py:138:    "describe_module": {"name": "nope_module_zz"},
origin/v3:platform/tests/test_actions_layer.py:32:CANVAS_NAMES = ["find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"]    # canvas-mcp-read: five reads whose actions l
origin/v3:platform/tests/test_aws_ce.py:810:                     "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_va
origin/v3:platform/tests/test_aws_launch.py:1161:                                          "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "list_figures", "my_usage", "find_mod
origin/v3:platform/tests/test_azure_ce.py:928:                     "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_
origin/v3:platform/tests/test_azure_launch.py:1119:                "read_task_log", "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get
origin/v3:platform/tests/test_azure_upload.py:830:                                      "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module
origin/v3:platform/tests/test_chat_confirm.py:373:BASE_TOOLS = ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get_validation",
origin/v3:platform/tests/test_chat_tools.py:15:READ_ONLY = {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files", "list_used_pipelines", "read_task_log", "r
origin/v3:platform/tests/test_cleanup_offer.py:807:    canvas = {"find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"}    # canvas-mcp-read
origin/v3:platform/tests/test_dataset_launch.py:213:    assert sorted(t.name for t in tools) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline
origin/v3:platform/tests/test_estimate_su.py:298:                     "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "g
origin/v3:platform/tests/test_gcb_ce.py:777:                     "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_va
origin/v3:platform/tests/test_gcb_launch.py:1069:                                          "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "list_figures", "my_usage", "find_mod
origin/v3:platform/tests/test_guidance.py:26:READ_TOOLS = ["get_compute_env", "get_run", "list_agents", "list_compute_envs", "list_runs", "list_site_files", "list_used_pipelines", "read_task_log", "ru
origin/v3:platform/tests/test_http_site_samplesheet.py:563:                                       "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "list_figures", "my_usage", "f
origin/v3:platform/tests/test_human_channel.py:158:    assert names == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get_valida
origin/v3:platform/tests/test_job_kinds_docs.py:9:            "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15}
origin/v3:platform/tests/test_k8s_ce.py:926:                     "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_va
origin/v3:platform/tests/test_keep_submissions.py:479:    for fname, needle in (("test_human_channel.py", '"cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env"'),
origin/v3:platform/tests/test_keep_submissions.py:704:    assert names == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get_val
origin/v3:platform/tests/test_launch_e2e.py:185:    assert sorted(t.name for t in tools) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "
origin/v3:platform/tests/test_launch_followup_e2e.py:51:    assert len(rows) == 2 and rows[0] == old[0] and rows[1][2] == 2231948
origin/v3:platform/tests/test_launch_platform.py:303:    assert sorted(t.name for t in ts) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline",
origin/v3:platform/tests/test_launch_profiles.py:444:    assert sorted(t.name for t in tools) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipelin
origin/v3:platform/tests/test_mcp.py:62:    assert sorted(t.name for t in tools) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run"
origin/v3:platform/tests/test_mcp.py:95:        assert sorted(t.name for t in tools) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_
origin/v3:platform/tests/test_mcp_canvas_read.py:17:NEW = ["find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"]
origin/v3:platform/tests/test_mcp_canvas_read.py:84:    r = tool_json(call(w, "describe_module", {"name": "fastqc"}))
origin/v3:platform/tests/test_mcp_canvas_read.py:86:    res = call(w, "describe_module", {"name": NO})
origin/v3:platform/tests/test_mcp_canvas_read.py:146:    for n, a in [("find_module", {"q": "fastqc"}), ("describe_module", {"name": "fastqc"}), ("list_pipelines", {}),
origin/v3:platform/tests/test_mcp_canvas_read.py:197:    layer = {"find_module": c.find_module, "describe_module": c.describe_module, "list_pipelines": p.list_pipelines,
origin/v3:platform/tests/test_mcp_canvas_read.py:215:    assert not hasattr(actions, "find_module") and not hasattr(actions, "describe_module")
origin/v3:platform/tests/test_mcp_server_doc.py:12:NUMBERS = {"six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixtee
origin/v3:platform/tests/test_mcp_server_doc.py:16:    "list_site_files", "list_used_pipelines", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation", "run_
origin/v3:platform/tests/test_mcp_server_doc.py:53:    found = re.findall(r"\b(six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen)\b read", DOC)
origin/v3:platform/tests/test_mcp_server_doc.py:106:    assert _first_line_problems("# ... offers fifteen read-only tools", 15) == []
origin/v3:platform/tests/test_mcp_server_doc.py:111:    assert _first_line_problems("# offers fifteen tools", 15)
origin/v3:platform/tests/test_mcp_server_doc.py:116:    assert _first_line_problems("# offers fifteen read-only tools ... ten ...", 15)
origin/v3:platform/tests/test_mcp_server_doc.py:126:    problems = _first_line_problems("# offers fifteen read-only tools", 17)
origin/v3:platform/tests/test_oauth_mcp.py:329:    assert names == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get_validation
origin/v3:platform/tests/test_owner_guard.py:204:                     "list_site_files", "list_used_pipelines", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_val
origin/v3:platform/tests/test_owner_guard.py:210:    assert canvas == {"find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"}
origin/v3:platform/tests/test_pat.py:281:    canvas = ["find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"]    # canvas-mcp-read
origin/v3:platform/tests/test_pat.py:374:    assert sorted(t.name for t in tools) == sorted(READ_NAMES + ["find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"] + WRITE_
origin/v3:platform/tests/test_resume_edit_params_platform.py:430:    assert sorted(t) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get
origin/v3:platform/tests/test_resume_entrypoints.py:45:    assert sorted(tools_of(rig)) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "g
origin/v3:platform/tests/test_station_envs.py:378:    want = ["get_compute_env", "get_run", "list_agents", "list_compute_envs", "list_runs", "list_site_files", "list_used_pipelines", "read_task_log", 
origin/v3:platform/tests/test_station_launch.py:731:                          "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "descri
origin/v3:platform/tests/test_su_usd.py:239:                     "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation", "delete_figure", "pack_figures", "publish_figure"
origin/v3:platform/tests/test_su_usd.py:242:    canvas = {"find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"}
origin/v3:platform/tests/test_web_board.py:1213:                                                    "list_site_files", "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "list_fig
origin/v3:platform/tests/test_web_guided_launch_preview.py:467:                     "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get
origin/v3:platform/tests/test_web_wording_sweep.py:116:    assert BANNED[:3] == ["用過", "選好", "寫死"] and len(BANNED) == 22 and len(NEW_WORDS) == 13 and BANNED_ALL == BANNED + NEW_WORDS
origin/v3:platform/tests/test_web_wording_sweep.py:138:    assert two_b.BANNED is BANNED and len(two_b.BANNED) == 22
```

同一條在工作樹（去掉 origin/v3，57 行）：

```
platform/tests/mcp/snapshots/tools.json:91:    "name": "describe_module"
platform/tests/mcp/test_mcp_contract_tools.py:18:    "my_usage", "run_outputs", "read_run_file", "list_figures", "read_task_log", "find_module", "describe_module", "list_pipelines",
platform/tests/mcp/test_mcp_contract_writes.py:138:    "describe_module": {"name": "nope_module_zz"},
platform/tests/test_actions_layer.py:33:CANVAS_NAMES = ["find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"]    # canvas-mcp-read: five reads whose actions live in the
platform/tests/test_aws_ce.py:810:                     "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation",
platform/tests/test_aws_launch.py:1161:                                          "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "des
platform/tests/test_azure_ce.py:928:                     "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation
platform/tests/test_azure_launch.py:1119:                "read_task_log", "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline"
platform/tests/test_azure_upload.py:830:                                      "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "descri
platform/tests/test_chat_confirm.py:373:BASE_TOOLS = ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get_validation",
platform/tests/test_chat_tools.py:15:READ_ONLY = {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files", "list_used_pipelines", "read_task_log", "run_outputs
platform/tests/test_cleanup_offer.py:807:    canvas = {"find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"}    # canvas-mcp-read
platform/tests/test_dataset_launch.py:213:    assert sorted(t.name for t in tools) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_ru
platform/tests/test_estimate_su.py:298:                     "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validat
platform/tests/test_gcb_ce.py:777:                     "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation",
platform/tests/test_gcb_launch.py:1069:                                          "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "des
platform/tests/test_guidance.py:26:READ_TOOLS = ["get_compute_env", "get_run", "list_agents", "list_compute_envs", "list_runs", "list_site_files", "list_used_pipelines", "read_task_log", "run_outputs"
platform/tests/test_http_site_samplesheet.py:563:                                       "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module
platform/tests/test_human_channel.py:158:    assert names == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get_validation", "la
platform/tests/test_job_kinds_docs.py:9:            "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15}
platform/tests/test_k8s_ce.py:926:                     "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation",
platform/tests/test_keep_submissions.py:479:    for fname, needle in (("test_human_channel.py", '"cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env"'),
platform/tests/test_keep_submissions.py:704:    assert names == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get_validation", 
platform/tests/test_launch_e2e.py:185:    assert sorted(t.name for t in tools) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", 
platform/tests/test_launch_followup_e2e.py:51:    assert len(rows) == 2 and rows[0] == old[0] and rows[1][2] == 2231948
platform/tests/test_launch_platform.py:303:    assert sorted(t.name for t in ts) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run"
platform/tests/test_launch_profiles.py:444:    assert sorted(t.name for t in tools) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_r
platform/tests/test_mcp.py:62:    assert sorted(t.name for t in tools) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get_val
platform/tests/test_mcp.py:95:        assert sorted(t.name for t in tools) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get
platform/tests/test_mcp_canvas_read.py:17:NEW = ["find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"]
platform/tests/test_mcp_canvas_read.py:84:    r = tool_json(call(w, "describe_module", {"name": "fastqc"}))
platform/tests/test_mcp_canvas_read.py:86:    res = call(w, "describe_module", {"name": NO})
platform/tests/test_mcp_canvas_read.py:146:    for n, a in [("find_module", {"q": "fastqc"}), ("describe_module", {"name": "fastqc"}), ("list_pipelines", {}),
platform/tests/test_mcp_canvas_read.py:197:    layer = {"find_module": c.find_module, "describe_module": c.describe_module, "list_pipelines": p.list_pipelines,
platform/tests/test_mcp_canvas_read.py:215:    assert not hasattr(actions, "find_module") and not hasattr(actions, "describe_module")
platform/tests/test_mcp_server_doc.py:12:NUMBERS = {"six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "s
platform/tests/test_mcp_server_doc.py:16:    "list_site_files", "list_used_pipelines", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation", "list_downstrea
platform/tests/test_mcp_server_doc.py:53:    found = re.findall(r"\b(six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen)\b read", DOC)
platform/tests/test_mcp_server_doc.py:106:    assert _first_line_problems("# ... offers fifteen read-only tools", 15) == []
platform/tests/test_mcp_server_doc.py:111:    assert _first_line_problems("# offers fifteen tools", 15)
platform/tests/test_mcp_server_doc.py:116:    assert _first_line_problems("# offers fifteen read-only tools ... ten ...", 15)
platform/tests/test_mcp_server_doc.py:126:    problems = _first_line_problems("# offers fifteen read-only tools", 18)
platform/tests/test_oauth_mcp.py:329:    assert names == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get_validation", "launch
platform/tests/test_owner_guard.py:204:                     "list_site_files", "list_used_pipelines", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation", 
platform/tests/test_owner_guard.py:210:    assert canvas == {"find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"}
platform/tests/test_pat.py:281:    canvas = ["find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"]    # canvas-mcp-read
platform/tests/test_pat.py:374:    assert sorted(t.name for t in tools) == sorted(READ_NAMES + ["find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"] + DOWNSTREAM_NAMES
platform/tests/test_resume_edit_params_platform.py:430:    assert sorted(t) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "ge
platform/tests/test_resume_entrypoints.py:45:    assert sorted(tools_of(rig)) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "
platform/tests/test_station_envs.py:378:    want = ["get_compute_env", "get_run", "list_agents", "list_compute_envs", "list_runs", "list_site_files", "list_used_pipelines", "read_task_log", "run_outpu
platform/tests/test_station_launch.py:731:                          "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module"
platform/tests/test_su_usd.py:239:                     "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation", "list_downstream", "delete_figure", "pack_figures", "publis
platform/tests/test_su_usd.py:242:    canvas = {"find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"}
platform/tests/test_web_board.py:1213:                                                    "list_site_files", "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "list_figures", "my
platform/tests/test_web_guided_launch_preview.py:467:                     "run_outputs", "read_run_file", "list_figures", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline"
platform/tests/test_web_wording_sweep.py:116:    assert BANNED[:3] == ["用過", "選好", "寫死"] and len(BANNED) == 22 and len(NEW_WORDS) == 13 and BANNED_ALL == BANNED + NEW_WORDS
platform/tests/test_web_wording_sweep.py:138:    assert two_b.BANNED is BANNED and len(two_b.BANNED) == 22
```

## 實際跑過的測試
本機（WSL，載入此工作樹的程式）只跑了動到的檔案：test_dataset_launch、test_launch_platform、test_mcp、test_resume_entrypoints、test_owner_guard、test_su_usd、test_mcp_server_doc、test_cleanup_offer、test_mcp_list_downstream、test_downstream_catalog、test_actions_layer、tests/mcp/，以及 tests/platform_storage_doc_test.sh 等 shell 測試。test_launch_e2e 本機無法跑（缺第二個固定版本的 Nextflow），其 tc010 名單是讀碼修的。全套測試由 CI 跑。

## Open: owner decision
test_tc010（platform/tests/test_launch_platform.py，唯讀工具的 `banned` 輸入欄位集合）目前是紅的：`list_downstream` 依計畫與維護者的規定帶一個 `pipeline` 參數，而 `banned` 含 `pipeline`。兩個選項：(a) 為此工具加一行豁免（比照既有的 read_task_log／run_name 豁免）；(b) 把參數改名。這是安全網斷言，沒有 owner 的同意不改，所以刻意留紅。

