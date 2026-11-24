#!/usr/bin/env bash
# Copy the server's live config files (with real values) into private-configs/ on your workstation.
#
# private-configs/ is git-ignored: it never leaves your machine. It has its own local git repository, so every
# run is a commit and you can see what changed on the server, and roll back.
#
# Usage: scripts/backup-private-configs.sh [ssh-host]     (default host: homeserver)
#        SSH_OPTS="-o HostKeyAlias=homeserver.local" scripts/backup-private-configs.sh user@192.168.1.50   (by IP)
# Secrets such as the Wi-Fi password are NOT copied (60-wifi.yaml is skipped).
set -euo pipefail
HOST="${1:-homeserver}"
SSH_OPTS="${SSH_OPTS:-}"
ssh() { command ssh $SSH_OPTS "$@"; }
DEST="$(cd "$(dirname "$0")/.." && pwd)/private-configs"
mkdir -p "$DEST"

# Files that hold real, non-public values: security settings and machine-specific identifiers.
FILES=(
  /etc/fail2ban/jail.local
  /etc/netplan/00-installer-config.yaml
  /etc/fstab
  /etc/avahi/avahi-daemon.conf
  /etc/ssh/sshd_config.d
  /etc/sudoers.d
  /etc/docker/daemon.json
  /etc/apt/apt.conf.d/52unattended-upgrades-local
  /etc/systemd/system/watchdog-driver.service
  /etc/systemd/system.conf.d
  /etc/systemd/journald.conf.d
  /etc/sysctl.d/90-panic-reboot.conf
  /etc/udev/rules.d/81-wifi-powersave-off.rules
  /opt/smart-home/compose.yaml
  /opt/smart-home/homeassistant/config/configuration.yaml
)

# Pack on the server (as root, skipping missing paths), unpack locally under private-configs/server/.
mkdir -p "$DEST/server"
ssh "$HOST" "sudo tar -czf - --ignore-failed-read ${FILES[*]} 2>/dev/null" | tar -xzf - -C "$DEST/server"

# State that isn't a file: firewall rules, effective SSH settings, fail2ban jail.
ssh "$HOST" 'sudo ufw status verbose; echo; sudo ufw show added' > "$DEST/ufw-rules.txt"
ssh "$HOST" 'sudo sshd -T | grep -E "^(passwordauthentication|pubkeyauthentication|permitrootlogin|kbdinteractiveauthentication) "' > "$DEST/sshd-effective.txt"
ssh "$HOST" 'sudo fail2ban-client status sshd' > "$DEST/fail2ban-status.txt" 2>&1 || true

cd "$DEST"
[ -d .git ] || git init -q
git add -A
if git diff --cached --quiet; then
  echo "No changes since the last backup."
else
  git -c commit.gpgsign=false commit -q -m "backup $(date '+%Y-%m-%d %H:%M') from $HOST"
  echo "Saved: $(git log --oneline -1)"
fi
