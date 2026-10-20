#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."
repo_root=$PWD
key="$repo_root/scripts/orca-vm/.ssh/id_ed25519"
image=orca-tapo-devcontainer:ssh
name="orca-tapo-${ORCA_VM_INSTANCE_ID:-$(date +%s)}"
auth_file="${CODEX_HOME:-$HOME/.codex}/auth.json"

docker image inspect "$image" >/dev/null 2>&1 || { echo "Run scripts/orca-vm/build.sh first" >&2; exit 1; }
[[ -f "$auth_file" ]] || { echo "Codex login file missing: $auth_file" >&2; exit 1; }
if [[ ! -f "$key" ]]; then
    mkdir -p "$(dirname "$key")"
    ssh-keygen -q -t ed25519 -N '' -f "$key"
fi

container_id=$(docker run -d --name "$name" -p 127.0.0.1::22 \
    -e "ORCA_SSH_PUBLIC_KEY=$(cat "$key.pub")" "$image")
trap 'docker logs "$container_id" >&2; docker rm -f "$container_id" >/dev/null' ERR
docker exec "$container_id" install -d -m 700 -o vscode -g vscode /home/vscode/.codex
docker cp "$auth_file" "$container_id:/home/vscode/.codex/auth.json"
docker exec "$container_id" chown vscode:vscode /home/vscode/.codex/auth.json
docker exec "$container_id" chmod 600 /home/vscode/.codex/auth.json
docker exec -u vscode "$container_id" codex login status >&2

port=$(docker port "$container_id" 22/tcp | tail -n 1 | sed 's/.*://')
for _ in {1..30}; do
    if docker exec "$container_id" test -f /etc/ssh/ssh_host_ed25519_key.pub; then break; fi
    sleep 1
done
host_key=$(docker exec "$container_id" cat /etc/ssh/ssh_host_ed25519_key.pub)
endpoint="[127.0.0.1]:$port"
mkdir -p "$HOME/.ssh"
ssh-keygen -R "$endpoint" -f "$HOME/.ssh/known_hosts" >/dev/null 2>&1 || true
printf '%s %s\n' "$endpoint" "$host_key" >> "$HOME/.ssh/known_hosts"
chmod 600 "$HOME/.ssh/known_hosts"

for _ in {1..30}; do
    if ssh -i "$key" -p "$port" -o BatchMode=yes -o IdentitiesOnly=yes \
        -o StrictHostKeyChecking=yes vscode@127.0.0.1 true 2>/dev/null; then break; fi
    sleep 1
done
ssh -i "$key" -p "$port" -o BatchMode=yes -o IdentitiesOnly=yes \
    -o StrictHostKeyChecking=yes vscode@127.0.0.1 true >&2

jq -n --arg id "$container_id" --arg key "$key" --argjson port "$port" \
    '{schemaVersion:1,connection:{type:"ssh",projectRoot:"/workspaces/home-assistant-tapo-p100",target:{label:"tapo-devcontainer",host:"127.0.0.1",port:$port,username:"vscode",identityFile:$key,identitiesOnly:true,portForwards:[{localPort:8123,remoteHost:"127.0.0.1",remotePort:8123,label:"Home Assistant"}]}},userData:{resourceId:$id}}'
trap - ERR
