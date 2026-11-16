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
見最後一次 commit 後的 `git diff --stat 2678ae99..HEAD`。
