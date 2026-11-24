#!/usr/bin/env bash
# Daily backup of the smart home server to the always-attached backup drive (docs/07-backups.md).
#
#   backup.sh run      health-check the drive, snapshot, archive, verify, rotate, write metrics
#   backup.sh verify   re-read every archive from the drive and check checksums + zstd integrity, write metrics
#
# Installed as /usr/local/sbin/smart-home-backup and run as root by systemd timers (configs/systemd/backup*.timer).
# Principles: docs/decisions/0002-backup-principles.md. Format: one plain (unencrypted) .tar.zst per day + .sha256.
set -Eeuo pipefail   # -E: the ERR trap also fires inside functions
umask 077

# ---- Settings (override via environment / systemd Environment=) -------------------------------------------------
BACKUP_MNT="${BACKUP_MNT:-/mnt/backup}"
BACKUP_DIR="${BACKUP_DIR:-$BACKUP_MNT/archives}"
KEEP_DAYS="${KEEP_DAYS:-7}"                         # archives older than this are deleted after a successful run
MIN_FREE_PCT="${MIN_FREE_PCT:-20}"                  # abort if the drive has less free space
STACK_DIR="${STACK_DIR:-/opt/smart-home}"
HA_CONFIG="${HA_CONFIG:-$STACK_DIR/homeassistant/config}"
TEXTFILE_DIR="${TEXTFILE_DIR:-/var/lib/node_exporter/textfile}"
WORK_DIR="${WORK_DIR:-/var/tmp/smart-home-backup}"

# What goes into the archive (absolute paths; missing ones are skipped).
INCLUDE=(
  "$STACK_DIR"                                       # compose, .env, secrets, Grafana DB, HA config, monitoring config
  /etc/netplan /etc/ufw /etc/fail2ban/jail.local /etc/ssh/sshd_config.d /etc/sudoers.d
  /etc/docker/daemon.json /etc/systemd/system /etc/systemd/system.conf.d /etc/systemd/journald.conf.d
  /etc/fstab /etc/avahi/avahi-daemon.conf /etc/sysctl.d /etc/udev/rules.d
  /etc/apt/apt.conf.d/52unattended-upgrades-local /etc/apt/sources.list.d /etc/apt/keyrings
  /etc/hostname /etc/hosts /var/lib/node_exporter/textfile
)
# Not needed or rebuilt automatically. The live HA database is replaced by a consistent snapshot.
EXCLUDE=(
  "${STACK_DIR#/}/victoriametrics"                   # metrics history: not backed up (decision in docs/07-backups.md)
  "${STACK_DIR#/}/grafana/plugins"                   # re-downloaded by Grafana
  "${HA_CONFIG#/}/home-assistant_v2.db"              # live DB (+ -wal/-shm): a snapshot is added instead
  "${HA_CONFIG#/}/home-assistant_v2.db-wal"
  "${HA_CONFIG#/}/home-assistant_v2.db-shm"
  "${HA_CONFIG#/}/.cache"
  "${HA_CONFIG#/}/tts"
  "${HA_CONFIG#/}/backups"
  "${HA_CONFIG#/}/home-assistant.log*"
  "*/__pycache__"
)
# ------------------------------------------------------------------------------------------------------------------

STEP="start"
START_TS=$(date +%s)
log() { echo "[backup] $*"; }

write_metrics() {   # write_metrics <file> <content>; atomic, so node_exporter never sees a half-written file
  mkdir -p "$TEXTFILE_DIR"
  printf '%s\n' "$2" > "$TEXTFILE_DIR/$1.tmp" && chmod 644 "$TEXTFILE_DIR/$1.tmp" && mv "$TEXTFILE_DIR/$1.tmp" "$TEXTFILE_DIR/$1"
}
prev_metric() {     # prev_metric <file> <name>: value from the previous metrics file, or 0
  awk -v n="$2" '$1 == n {print $2}' "$TEXTFILE_DIR/$1" 2>/dev/null | tail -1 | grep . || echo 0
}
direct_read() {     # read a file from the drive itself, not from the page cache
  # O_DIRECT reads fail with EINVAL on some USB flash drives, so instead drop the file's cached pages first
  # (the data is already synced), then read it normally from the device.
  dd if="$1" iflag=nocache count=0 status=none
  dd if="$1" bs=1M status=none
}

# ---- Drive health checks (principle 3) ---------------------------------------------------------------------------
check_drive() {
  # Note: every check is a plain command or an explicit "if ...; then false; fi". set -e ignores failures of
  # commands negated with "!" and of all but the last command in an "a && b" list.
  STEP="drive_mounted"
  mountpoint -q "$BACKUP_MNT"
  [ -f "$BACKUP_MNT/.backup-target" ]
  STEP="drive_writable"
  if findmnt -no OPTIONS "$BACKUP_MNT" | tr ',' '\n' | grep -qx ro; then false; fi
  STEP="drive_free_space"
  local used; used=$(df --output=pcent "$BACKUP_MNT" | tail -1 | tr -dc '0-9')
  [ $((100 - used)) -ge "$MIN_FREE_PCT" ]
  STEP="drive_fs_errors"
  local dev; dev=$(findmnt -no SOURCE "$BACKUP_MNT")
  if tune2fs -l "$dev" 2>/dev/null | grep -q "^FS Error count"; then false; fi
  STEP="drive_io_errors"
  local disk; disk=$(lsblk -no PKNAME "$dev" | head -1)
  if journalctl -k --since "-24h" --no-pager -q | grep -E "(I/O error|EXT4-fs error)" | grep -q "${disk:-__none__}"; then false; fi
  STEP="drive_read_write"
  local t="$BACKUP_MNT/.rwtest" a b
  head -c 4M /dev/urandom > "$WORK_DIR/rwtest"
  a=$(sha256sum < "$WORK_DIR/rwtest" | cut -d' ' -f1)
  dd if="$WORK_DIR/rwtest" of="$t" bs=1M conv=fsync status=none
  b=$(direct_read "$t" | sha256sum | cut -d' ' -f1)
  rm -f "$t" "$WORK_DIR/rwtest"
  [ "$a" = "$b" ]
}

on_error() {
  local rc=$?
  log "FAILED at step: $STEP (exit $rc)"
  write_metrics backup.prom "# HELP smart_home_backup_last_run_timestamp_seconds Last backup run (success or failure).
# TYPE smart_home_backup_last_run_timestamp_seconds gauge
smart_home_backup_last_run_timestamp_seconds $(date +%s)
# HELP smart_home_backup_last_run_success 1 if the last backup run succeeded.
# TYPE smart_home_backup_last_run_success gauge
smart_home_backup_last_run_success 0
# HELP smart_home_backup_last_failed_step Step where the last run failed (value always 1).
# TYPE smart_home_backup_last_failed_step gauge
smart_home_backup_last_failed_step{step=\"$STEP\"} 1
# HELP smart_home_backup_last_success_timestamp_seconds Last successful backup.
# TYPE smart_home_backup_last_success_timestamp_seconds gauge
smart_home_backup_last_success_timestamp_seconds $(prev_metric backup.prom smart_home_backup_last_success_timestamp_seconds)"
  rm -f "$BACKUP_DIR"/*.partial "$BACKUP_MNT/.rwtest"
  exit "$rc"
}

cmd_run() {
  trap on_error ERR
  mkdir -p "$WORK_DIR"; rm -rf "${WORK_DIR:?}"/*
  check_drive
  mkdir -p "$BACKUP_DIR"

  STEP="ha_db_snapshot"     # SQLite online backup API: a consistent copy while Home Assistant keeps writing
  mkdir -p "$WORK_DIR/snap"
  if [ -f "$HA_CONFIG/home-assistant_v2.db" ]; then
    sqlite3 "$HA_CONFIG/home-assistant_v2.db" ".timeout 30000" ".backup '$WORK_DIR/snap/home-assistant_v2.db'"
    [ "$(sqlite3 "$WORK_DIR/snap/home-assistant_v2.db" 'PRAGMA quick_check;')" = "ok" ]
  fi

  STEP="archive"
  local name ex=() paths=() p
  name="backup-$(date +%F).tar.zst"
  for p in "${EXCLUDE[@]}"; do ex+=(--exclude="$p"); done
  for p in "${INCLUDE[@]}"; do [ -e "$p" ] && paths+=("${p#/}"); done
  tar -C / --anchored --warning=no-file-changed -cf "$WORK_DIR/backup.tar" "${ex[@]}" "${paths[@]}" || [ $? -eq 1 ]
  if [ -f "$WORK_DIR/snap/home-assistant_v2.db" ]; then
    tar -C "$WORK_DIR/snap" -rf "$WORK_DIR/backup.tar" --transform "s|^|${HA_CONFIG#/}/|" home-assistant_v2.db
  fi
  zstd -q -T0 -10 "$WORK_DIR/backup.tar" -o "$WORK_DIR/$name"
  (cd "$WORK_DIR" && sha256sum "$name" > "$name.sha256")

  STEP="copy_to_drive"
  cp "$WORK_DIR/$name" "$BACKUP_DIR/$name.partial"
  sync -f "$BACKUP_DIR"

  STEP="verify_on_drive"    # read back from the drive (not from cache) and compare
  [ "$(direct_read "$BACKUP_DIR/$name.partial" | sha256sum | cut -d' ' -f1)" = "$(cut -d' ' -f1 "$WORK_DIR/$name.sha256")" ]
  direct_read "$BACKUP_DIR/$name.partial" | zstd -q -t
  mv "$BACKUP_DIR/$name.partial" "$BACKUP_DIR/$name"
  cp "$WORK_DIR/$name.sha256" "$BACKUP_DIR/$name.sha256"
  sync -f "$BACKUP_DIR"

  STEP="rotate"             # keep the last KEEP_DAYS days; only after a verified new archive exists
  find "$BACKUP_DIR" -maxdepth 1 -name 'backup-*.tar.zst*' -mtime "+$((KEEP_DAYS - 1))" -delete

  STEP="metrics"
  local size count now
  size=$(stat -c %s "$BACKUP_DIR/$name"); count=$(find "$BACKUP_DIR" -maxdepth 1 -name 'backup-*.tar.zst' | wc -l); now=$(date +%s)
  write_metrics backup.prom "# HELP smart_home_backup_last_run_timestamp_seconds Last backup run (success or failure).
# TYPE smart_home_backup_last_run_timestamp_seconds gauge
smart_home_backup_last_run_timestamp_seconds $now
# HELP smart_home_backup_last_run_success 1 if the last backup run succeeded.
# TYPE smart_home_backup_last_run_success gauge
smart_home_backup_last_run_success 1
# HELP smart_home_backup_last_success_timestamp_seconds Last successful backup.
# TYPE smart_home_backup_last_success_timestamp_seconds gauge
smart_home_backup_last_success_timestamp_seconds $now
# HELP smart_home_backup_last_duration_seconds Duration of the last successful run.
# TYPE smart_home_backup_last_duration_seconds gauge
smart_home_backup_last_duration_seconds $((now - START_TS))
# HELP smart_home_backup_last_size_bytes Size of the newest archive.
# TYPE smart_home_backup_last_size_bytes gauge
smart_home_backup_last_size_bytes $size
# HELP smart_home_backup_archives Number of archives on the drive.
# TYPE smart_home_backup_archives gauge
smart_home_backup_archives $count"
  rm -rf "${WORK_DIR:?}"/*
  log "OK: $name ($size bytes, $count archives, $((now - START_TS)) s)"
}

cmd_verify() {
  local ok=1 checked=0 failed=0 f expected actual
  STEP="drive_mounted"
  if ! mountpoint -q "$BACKUP_MNT" || [ ! -f "$BACKUP_MNT/.backup-target" ]; then ok=0   # explicit branch, not set -e
  else
    for f in "$BACKUP_DIR"/backup-*.tar.zst; do
      [ -e "$f" ] || continue
      checked=$((checked + 1))
      expected=$(cut -d' ' -f1 "$f.sha256" 2>/dev/null || true)
      actual=$(direct_read "$f" | sha256sum | cut -d' ' -f1)
      if [ -n "$expected" ] && [ "$expected" = "$actual" ] && direct_read "$f" | zstd -q -t; then
        log "verify OK: $(basename "$f")"
      else
        log "verify FAILED: $(basename "$f")"; failed=$((failed + 1)); ok=0
      fi
    done
    [ "$checked" -gt 0 ] || ok=0
  fi
  write_metrics backup_verify.prom "# HELP smart_home_backup_verify_timestamp_seconds Last verification of all archives.
# TYPE smart_home_backup_verify_timestamp_seconds gauge
smart_home_backup_verify_timestamp_seconds $(date +%s)
# HELP smart_home_backup_verify_success 1 if every archive passed checksum and zstd integrity checks.
# TYPE smart_home_backup_verify_success gauge
smart_home_backup_verify_success $ok
# HELP smart_home_backup_verify_archives_checked Archives checked in the last verification.
# TYPE smart_home_backup_verify_archives_checked gauge
smart_home_backup_verify_archives_checked $checked
# HELP smart_home_backup_verify_archives_failed Archives that failed the last verification.
# TYPE smart_home_backup_verify_archives_failed gauge
smart_home_backup_verify_archives_failed $failed"
  [ "$ok" = 1 ]
}

exec 9>/run/smart-home-backup.lock
flock -n 9 || { log "another backup/verify run is in progress"; exit 1; }
case "${1:-}" in
  run) cmd_run ;;
  verify) cmd_verify ;;
  *) echo "usage: $0 run|verify" >&2; exit 2 ;;
esac
