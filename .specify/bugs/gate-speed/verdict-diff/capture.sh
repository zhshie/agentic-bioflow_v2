#!/bin/bash
# Capture every stdin payload that the gate tests feed to the four hooks.
SRC=/mnt/c/Users/ACER/Desktop/agentic-bioflow/wt-34-base
CAP=/tmp/abf34_cap
rm -rf "$CAP" /tmp/abf34_corpus_raw; mkdir -p "$CAP" /tmp/abf34_corpus_raw
cp -r "$SRC"/. "$CAP"/ 2>/dev/null
cd "$CAP" || exit 1
for n in confirm_launch confirm_cleanup confirm_walkthrough guard_plugin_files; do
  mv "hooks/$n.sh" "hooks/$n.real.sh"
  cat > "hooks/$n.sh" <<EOF
#!/bin/bash
d="\${0%/*}"
f=\$(mktemp "/tmp/abf34_corpus_raw/$n.XXXXXX")
cat > "\$f"
bash "\$d/$n.real.sh" < "\$f"
exit \$?
EOF
  chmod +x "hooks/$n.sh" "hooks/$n.real.sh"
done
for t in "$@"; do
  echo "=== $t"
  bash "tests/$t" > "/tmp/abf34_cap_$t.log" 2>&1
  tail -3 "/tmp/abf34_cap_$t.log"
done
ls /tmp/abf34_corpus_raw | wc -l
