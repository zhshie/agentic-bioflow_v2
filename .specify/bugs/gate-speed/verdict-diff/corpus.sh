#!/bin/bash
# Build the verdict-diff corpus: every payload the gate tests fed the hooks (captured
# from the baseline), plus 50 harmless everyday commands and a set of odd shapes.
OUT=/tmp/abf34_corpus
rm -rf "$OUT"; mkdir -p "$OUT"
n=0
# 1. captured payloads, de-duplicated by content
for f in /tmp/abf34_corpus_raw/*; do
  sum=$(md5sum < "$f" | cut -d' ' -f1)
  [ -e "$OUT/.seen-$sum" ] && continue
  : > "$OUT/.seen-$sum"
  n=$((n+1)); cp "$f" "$OUT/cap-$(printf %04d $n).raw"
done
rm -f "$OUT"/.seen-*
echo "captured unique: $n"

mk() { # mk <name> <tool> <json tool_input object>
  jq -nc --arg t "$2" --argjson i "$3" '{session_id:"s1", cwd:"@CWD@", transcript_path:"@TP@", hook_event_name:"PreToolUse", tool_name:$t, tool_input:$i}' > "$OUT/$1.json"
}
bash_cmd() { mk "$1" Bash "$(jq -nc --arg c "$2" '{command:$c}')"; }

i=0
while IFS= read -r c; do
  [ -n "$c" ] || continue
  i=$((i+1)); bash_cmd "easy-$(printf %03d $i)" "$c"
done <<'EOF'
ls -la
pwd
git status
git diff --stat
git log --oneline -5
cat README.md
head -20 notes.txt
tail -f app.log
grep -rn "foo" src/
grep -rn x results/
find . -name "*.py" | head
wc -l *.sh
echo hello world
echo "tw launch is a command"
cd src && ls
mkdir -p build/out
cp a.txt b.txt
mv old.txt new.txt
python3 -c "print(1+1)"
python3 script.py --input data.csv
npm test
npm run build
make -j4
curl -s https://example.com | head
jq . package.json
sed -n 1,10p file.txt
awk '{print $1}' data.tsv
sort data.txt | uniq -c | sort -rn | head
diff a.txt b.txt
du -sh .
df -h
ps aux | grep python
which jq
bash tests/run_all.sh --only gate
gh issue view 34 -R zhshie/agentic-bioflow_v2
git commit -m "fix: speed"
git push
tar czf out.tgz dir/
touch newfile
chmod +x run.sh
for f in a b c; do echo $f; done
if [ -f x ]; then echo yes; else echo no; fi
export FOO=bar && echo $FOO
date +%s
sleep 1
ls results/
cat results/summary.txt
ls rawdata/ analysis/ work/
squeue -u me
tw runs list
ssh host hostname
rsync -av a/ b/
EOF
echo "easy: $i"

# odd shapes
bash_cmd odd-heredoc "$(printf 'cat > notes.md <<%s\nSubmit with: tw launch x\nrm -rf results\nEOF\nls' "'EOF'")"
bash_cmd odd-heredoc-bash "$(printf 'bash <<%s\ntw launch x\nEOF' "'EOF'")"
bash_cmd odd-heredoc-py "$(printf 'python3 - <<%s\nimport os\nos.system("ls")\nEOF' "'EOF'")"
bash_cmd odd-heredoc-write-analysis "$(printf 'cat > analysis/de.R <<%s\nlibrary(x)\nEOF' "'EOF'")"
bash_cmd odd-multiline "$(printf 'ls\ntw\nlaunch x')"
bash_cmd odd-multiline2 "$(printf 'bash agent_ctl.sh\nstart')"
bash_cmd odd-multiline3 "$(printf 'cd x\ntw launch nf-core/rnaseq')"
bash_cmd odd-quote-assemble 'tw la"x"unch y'
bash_cmd odd-quote-assemble2 's"x"sh host ls'
bash_cmd odd-quote-assemble3 'ss""h host ls'
bash_cmd odd-trailing-newline "$(printf 'ls -la\n\n')"
bash_cmd odd-continuation "$(printf 'tw la\\\nunch x')"
bash_cmd odd-subst 'echo $(tw launch x)'
bash_cmd odd-bashc "bash -c 'nextflow run x'"
bash_cmd odd-ssh-batch "ssh -o BatchMode=yes host ls"
bash_cmd odd-wsl "wsl ssh host ls"
bash_cmd odd-onsite "bash scripts/on_site.sh 'ls'"
bash_cmd odd-sbatch "sbatch job.sh"
bash_cmd odd-relaunch "tw runs relaunch 123"
bash_cmd odd-launch-nodis "tw launch nf-core/rnaseq --profile test"
bash_cmd odd-launch-dis "tw launch nf-core/rnaseq --disable-optimization"
bash_cmd odd-restart "bash scripts/egress_ctl.sh restart"
bash_cmd odd-agent-start "scripts/agent_ctl.sh start"
bash_cmd odd-setting "bash scripts/settings.sh --set agent_connection 123"
bash_cmd odd-rm-results "rm -rf results"
bash_cmd odd-rm-work "rm -rf work"
bash_cmd odd-rm-var 'rm -rf "$RUN_DIR/results"'
bash_cmd odd-rm-root "rm -rf /"
bash_cmd odd-rm-plugins "rm -rf .nextflow/plugins"
bash_cmd odd-rm-shared "rm -rf _references"
bash_cmd odd-mv-results "mv results results.bak"
bash_cmd odd-glob "rm -rf res*"
bash_cmd odd-truncate "echo x > results/a.txt"
bash_cmd odd-fastq "rm sample.fastq.gz"
bash_cmd odd-find-delete "find work -name '*.tmp' -delete"
bash_cmd odd-gitclean "git clean -fd"
bash_cmd odd-cd-rm "cd results && rm -rf x"
bash_cmd odd-pycode "python3 -c 'import shutil; shutil.rmtree(\"results\")'"
bash_cmd odd-gen-samplesheet "python3 scripts/generate_samplesheet.py --input x"
bash_cmd odd-datasets "tw datasets add x"
bash_cmd odd-params "cat > params.yml <<'EOF'
outdir: /tmp/out
EOF"
bash_cmd odd-gh-comment 'gh issue comment 1 --body "generate_samplesheet.py decides"'
bash_cmd odd-tee-analysis "echo x | tee analysis/plot.R"
bash_cmd odd-plugin-write 'cp x @ROOT@/hooks/a.sh'
bash_cmd odd-plugin-redirect 'echo x > @ROOT@/hooks/a.sh'
bash_cmd odd-plugin-read 'cat @ROOT@/hooks/a.sh'
bash_cmd odd-plugin-var 'rm $CLAUDE_PLUGIN_ROOT/hooks/a.sh'
bash_cmd odd-plugin-cd 'cd @ROOT@ && rm hooks/a.sh'
bash_cmd odd-plugin-tilde 'rm ~/.claude/plugins/cache/x/y'
bash_cmd odd-plugin-grep 'grep -n foo @ROOT@/hooks/x.sh > /tmp/out'
bash_cmd odd-empty ''
bash_cmd odd-spaces '   '
bash_cmd odd-unicode 'echo "略過導覽"'
mk odd-write-egress Write '{"file_path":"/x/y/egress_allow.tsv","content":"a"}'
mk odd-write-analysis Write '{"file_path":"/x/analysis/de.R","content":"library(x)"}'
mk odd-write-analysis2 Edit '{"file_path":"analysis/plot.py","old_string":"a","new_string":"b"}'
mk odd-write-samplesheet Write '{"file_path":"/x/samplesheet.csv","content":"a,b"}'
mk odd-write-params Write '{"file_path":"/x/params.yaml","content":"outdir: /tmp/o"}'
mk odd-write-params2 Write '{"file_path":"/x/params.yaml","content":"outdir: /x/projects/p/runs/r"}'
mk odd-write-plugin Write '{"file_path":"@ROOT@/hooks/new.sh","content":"x"}'
mk odd-write-plugin2 Edit '{"file_path":"@ROOT@/skills/a.md","old_string":"a","new_string":"b"}'
mk odd-write-plain Write '{"file_path":"/tmp/a.txt","content":"hello"}'
mk odd-notebook NotebookEdit '{"notebook_path":"/x/analysis/n.ipynb","new_source":"x"}'
mk odd-multiedit MultiEdit '{"file_path":"/x/analysis/a.R","edits":[]}'
mk odd-ps PowerShell '{"command":"Remove-Item results -Recurse"}'
mk odd-ps2 PowerShell '{"command":"Get-ChildItem"}'
mk odd-ps3 PowerShell '{"script":"nextflow run x"}'
mk odd-ps-unknown-field PowerShell '{"weird":"Remove-Item results"}'
mk odd-ps-unknown-field2 Terminal '{"weird":"tw launch x"}'
mk odd-ps-unknown-plain PowerShell '{"weird":"ls"}'
mk odd-mcp-launch mcp__seqera__launch_pipeline '{"pipeline":"x"}'
mk odd-mcp-query mcp__seqera__list_runs '{"w":1}'
mk odd-mcp-other mcp__shellthing__run '{"weird":"ssh host"}'
mk odd-tool-unknown Foo '{"a":1}'
mk odd-bash-notstring Bash '{"command":{"a":"b"}}'
mk odd-bash-number Bash '{"command":5}'
mk odd-bash-null Bash '{"command":null}'
mk odd-bash-script Bash '{"script":"tw launch y"}'
mk odd-input-string Bash '"just a string"'
printf '%s' '{"session_id":"s1","tool_name":"Bash","tool_input":"x"}' > "$OUT/odd-toolinput-string.json"
printf '%s' '[1,2]' > "$OUT/odd-array.json"
printf '%s' '' > "$OUT/odd-empty-input.raw"
printf '%s' 'not json at all tw launch' > "$OUT/odd-nonjson-launch.raw"
printf '%s' 'not json at all rm -rf x' > "$OUT/odd-nonjson-rm.raw"
printf '%s' 'plain text' > "$OUT/odd-nonjson-plain.raw"
printf '%s' '{"session_id":"s1","tool_name":"Bash","tool_input":{"command":"ls"}}{"session_id":"s1","tool_name":"Bash","tool_input":{"command":"tw launch x"}}' > "$OUT/odd-two-docs.json"
printf '%s\n' '{"session_id":"s1","tool_name":"Bash\n","tool_input":{"command":"ls\n\n"}}' | sed 's/\\n/\\n/g' > "$OUT/odd-tool-trailing-nl.json"
printf '%s' '{"session_id":"s1","tool_name":"Bash","tool_input":{"command":"a\u001fb"}}' > "$OUT/odd-sep-in-field.json"
printf '%s' '{"tool_name":"Bash","tool_input":{"command":"tw launch x"}}' > "$OUT/odd-no-session.json"
ls "$OUT" | wc -l
