#!/bin/sh
set -eu

mkdir -p /backups

while true; do
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  temporary="/backups/ai-polyphite-${timestamp}.dump.tmp"
  destination="/backups/ai-polyphite-${timestamp}.dump"

  pg_dump --format=custom --file="${temporary}"
  pg_restore --list "${temporary}" >/dev/null
  mv "${temporary}" "${destination}"
  sha256sum "${destination}" >"${destination}.sha256"
  find /backups -type f -name 'ai-polyphite-*.dump*' \
    -mtime "+${BACKUP_RETENTION_DAYS}" -delete

  sleep "${BACKUP_INTERVAL_SECONDS}"
done
