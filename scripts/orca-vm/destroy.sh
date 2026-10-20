#!/usr/bin/env bash
set -euo pipefail

payload=$(cat)
id=$(jq -r '.recipeResult.userData.resourceId // empty' <<< "$payload")
[[ -n "$id" ]] || { echo 'Missing container id in recipe result' >&2; exit 1; }
if docker container inspect "$id" >/dev/null 2>&1; then
    port=$(docker port "$id" 22/tcp | tail -n 1 | sed 's/.*://' || true)
    host_key=$(docker exec "$id" cat /etc/ssh/ssh_host_ed25519_key.pub 2>/dev/null || true)
    endpoint="[127.0.0.1]:$port"
    if [[ -n "$port" && -n "$host_key" && -f "$HOME/.ssh/known_hosts" ]] && grep -Fqx "$endpoint $host_key" "$HOME/.ssh/known_hosts"; then
        ssh-keygen -R "$endpoint" -f "$HOME/.ssh/known_hosts" >/dev/null
    fi
fi
docker rm -f "$id" >/dev/null
