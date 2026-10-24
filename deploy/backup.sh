#!/usr/bin/env bash
# Back up what cannot be rebuilt (docs/OPERATIONS.md, section 4).
#
# Usage: deploy/backup.sh <destination-folder>
#
# Makes <destination-folder>/abf-backup-<UTC time>/ holding tokens.db, platform.db,
# web_signing.key (if web ever started), uploads/ and records/. The two databases are copied
# with SQLite's own backup, so a copy taken while the services write is still whole. The
# run index is left out on purpose: the rebuild command (OPERATIONS, section 4) makes it again.
# The folder is mode 700 and the files 600. Nothing is sent anywhere, and old backups are
# never deleted; moving a backup off this machine is a step for the operator.
# The data folder is found as the services find it: ABF_PLATFORM_DB, else
# ${XDG_DATA_HOME:-~/.local/share}/abf-platform/; ABF_PLATFORM_TOKENS, ABF_PLATFORM_STATE and
# ABF_PLATFORM_UPLOADS move single items, the same way.
set -euo pipefail

if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
  echo "Give the destination folder to put the backup in, for example: deploy/backup.sh ~/backups" >&2
  exit 2
fi
dest_root=$1

if [ -n "${ABF_PLATFORM_DB:-}" ]; then
  data_dir=$(dirname -- "$ABF_PLATFORM_DB")
else
  data_dir=${XDG_DATA_HOME:-$HOME/.local/share}/abf-platform
fi
tokens=${ABF_PLATFORM_TOKENS:-$data_dir/tokens.db}
state=${ABF_PLATFORM_STATE:-$data_dir/platform.db}
state_dir=$(dirname -- "$state")
uploads=${ABF_PLATFORM_UPLOADS:-$state_dir/uploads}
records=$state_dir/records
key=$state_dir/web_signing.key

for need in "tokens.db:$tokens" "platform.db:$state"; do
  if [ ! -f "${need#*:}" ]; then
    echo "Cannot back up: ${need%%:*} is missing (looked for ${need#*:}). Check ABF_PLATFORM_DB, or run this as the user that runs the services." >&2
    exit 1
  fi
done

umask 077
mkdir -p -- "$dest_root"
out=$dest_root/abf-backup-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -- "$out"

backup_db() { # <source> <copy>
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$1" ".backup '$2'"
  else
    python3 -c 'import sqlite3, sys
src = sqlite3.connect(sys.argv[1]); dst = sqlite3.connect(sys.argv[2])
src.backup(dst); dst.close(); src.close()' "$1" "$2"
  fi
}
backup_db "$tokens" "$out/tokens.db"
backup_db "$state" "$out/platform.db"

if [ -f "$key" ]; then
  cp -- "$key" "$out/web_signing.key"
else
  echo "web has not been started yet, so there is no signing key to back up; skipped."
fi
if [ -d "$uploads" ]; then cp -R -- "$uploads" "$out/uploads"; else echo "No uploads folder yet; skipped."; fi
if [ -d "$records" ]; then cp -R -- "$records" "$out/records"; else echo "No records folder yet; skipped."; fi

echo "Backup written to $out"
