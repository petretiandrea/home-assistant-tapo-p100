#!/usr/bin/env bash
set -euo pipefail

: "${ORCA_SSH_PUBLIC_KEY:?missing SSH public key}"
ln -sf /usr/local/share/nvm/current/bin/node /usr/local/bin/node
ln -sf /usr/local/share/nvm/current/bin/codex /usr/local/bin/codex
install -d -m 700 -o vscode -g vscode /home/vscode/.ssh
printf '%s\n' "$ORCA_SSH_PUBLIC_KEY" > /home/vscode/.ssh/authorized_keys
chown vscode:vscode /home/vscode/.ssh/authorized_keys
chmod 600 /home/vscode/.ssh/authorized_keys
ssh-keygen -A >/dev/null
exec /usr/sbin/sshd -D -e
