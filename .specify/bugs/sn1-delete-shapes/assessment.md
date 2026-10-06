# Bug Assessment: deletes of rawdata/, results/ and analysis/ that the guard does not see

- **Slug**: sn1-delete-shapes
- **Created**: 2026-10-05
- **Source**: fresh audit against constitution 2.0.0 (`C:\Users\ACER\abf_audit2\probes.txt`, `probes2.txt`, `probe.out`)
- **Verdict**: valid
- **Severity**: high (Safety Net 1: these delete the user's source data, or the pipeline's output, with nothing printed)

## 給維護者

1. 安全網第 1 條：rawdata/、results/、analysis/（以及 _references/、共用映像庫、.nextflow/plugins/）永遠不刪。關卡認得 `rm`、`find -delete`、`rsync --delete` 等寫法，但還有一批「其實也會刪掉」的寫法完全不出聲：打包後刪原檔（`tar --remove-files`、`zip -m`）、雲端同步工具（`rclone purge/delete/move/sync`）、在 node 或 ruby 程式碼裡刪、用大括號拼出名字（`res{ults,}`）、大小寫不同（`RESULTS`，Windows 與 macOS 的檔案系統不分大小寫，就是同一個資料夾）、用連結蓋掉（`ln -sfn /tmp/x results`）、把權限改成誰都打不開（`install -d -m 000 results`）。
2. 另外兩個「判斷不一致」：`truncate -s 0 rawdata/x.fastq.gz` 會被擋，但效果完全相同的 `: > rawdata/x.fastq.gz` 只給提醒；`find <分析區> -name '*.fastq.gz' -delete` 會把 rawdata/ 裡的定序檔全刪，也只給提醒。而 `find <分析區> -delete`、`rm -rf <分析區>`（連 results/ 一起刪）甚至什麼都不說。
3. 修法：每一種寫法都找出「真正被刪的是哪個路徑」，再用跟 `rm` 相同的規則判斷；確定是受保護資料夾就拒絕，不確定（變數、萬用字元、看不到內容）就請使用者確認，不再放行。明確在受保護資料夾以外的刪除行為不變。

## Reproduction (WSL, 29e7b98, `probe.sh` against this worktree)

| Command (`<run>` = /work/u1/lab_runs/x) | Verdict | Should be |
|---|---|---|
| `tar --remove-files -cf /tmp/r.tar <run>/results` | pass | deny |
| `zip -rm /tmp/r.zip <run>/results` | pass | deny |
| `rclone purge <run>/results` | pass | deny |
| `node -e "require('fs').rmSync('<run>/results',{recursive:true})"` | pass | ask (as python's shutil.rmtree) |
| `ruby -e 'require "fileutils"; FileUtils.rm_rf("<run>/results")'` | pass | ask |
| `rm -rf <run>/res{ults,}` | pass | deny |
| `rm -rf <run>/RESULTS` | pass | deny where names ignore case (Windows, macOS); ask elsewhere |
| `ln -sfn /tmp/x <run>/results` | pass | deny |
| `install -d -m 000 <run>/results` | pass | ask (it removes nothing; it locks everyone out) |
| `: > <run>/rawdata/s1.fastq.gz` | warn | deny (= `truncate -s 0`, which denies) |
| `find <run> -name '*.fastq.gz' -delete` | warn | deny |
| `find <run> -delete`, `rm -rf <run>` | pass | deny (both remove results/ with the rest) |

Already acceptable and kept: `resul*`, `result?`, `$(echo …/results)`, `R=…/results; rm -rf "$R"` ask (the guard cannot see the target); `mv results /tmp/x`, `rclone move` ask (moving out, maintainer decision E9).

## Root Cause (high confidence)

`hooks/confirm_cleanup.sh` decides "is this a delete" from a fixed set of verbs (rm/rmdir/unlink/shred/truncate, find -delete/-exec, rsync --delete, git clean, Remove-Item, cmd rd/del) and code calls (`shutil.rmtree(`, `os.remove(`, `fs.rmSync(` ...). Everything else is not judged at all. Within the judged set:
- a brace word is flattened (`{`, `}` and `,` become `/`), which recovers `{results,work}` but not `res{ults,}`;
- names are compared case-sensitively;
- a redirect is never a delete, so a truncation by redirect goes to the overwrite warning, and only for an absolute target;
- a find is judged by its root's own name, so a root above rawdata/ looks harmless, and its `-name` filter only reaches the sequencing-file warning;
- `node`'s `require('fs').rmSync(` does not match `fs\.rmSync\(`, and Ruby's FileUtils is not in the list.

## Proposed Remediation

- `tar … --remove-files`: every source is a delete target (not the archive after `-f`/`--file`, not the `-C` folder); `-T`/`--files-from`: sources unknown, ask.
- `zip -m`/`--move`: every name after the zip file is a delete target (not `-x`/`-i` patterns); `-@`: unknown, ask.
- `rclone purge|delete|deletefile|rmdir|rmdirs`: every path is a delete target; `sync`: the destination; `move|moveto`: the sources, as an `mv` source (ask); `remote:` prefixes judged with and without; `--dry-run`/`-n` deletes nothing.
- Code deletes: any `.rm(`/`.rmdir(`/`.unlink(` call and the node `*Sync` forms, Ruby `FileUtils.rm*`/`remove*` (with or without parentheses), bare `rm_rf(`/`remove_dir(`, `File/Dir.delete(`: ask, as for python.
- Brace words are expanded the way bash does (lists, nesting, `a..z`/`1..9` sequences, at most 64 words; more is unknown, ask), and every word judged; the old flattening is kept too.
- Names are compared ignoring case where the file system does (Git Bash, Cygwin, macOS, or a Windows-shaped path anywhere): deny. Elsewhere a protected name in another case asks.
- `ln` with `-f`: a link name that IS a guarded folder (not a path inside it) is judged as deleted. `install -d` with a mode or owner on a folder that is protected: ask.
- A pure truncation (`: >`, `>`, `true >`, `cat /dev/null >`, `echo -n >`, `printf >`; not `>>`): its targets are judged as deleted, relative ones against the working folder.
- A recursive delete (`rm -r`, `find … -delete`/`-exec rm`) of a folder that holds protected folders (by the deployment layout: `…/lab_runs/<x>`, `…/projects[/<p>]`, `…/runs[/<r>]`; or on this machine, it has a `rawdata/`, `results/`, `analysis/` or `_references/` child): deny. A find from such a folder that has a name filter: deny when the filter names sequencing files, ask otherwise. A find filtered on sequencing files from a folder the guard cannot place: ask (`/tmp` and `$TMPDIR` excepted: unchanged).
- Each trigger joins the large-input filter (#62); tests first in `tests/confirm_cleanup_test.sh`, each shape with a control that must not change.
- Out of scope: `apptainer`/`singularity cache clean` and `~/.apptainer/cache` (a personal cache, not the lab's shared library); `gzip` replacing a file by its compressed copy; `chmod`.
