#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."
npx --yes @devcontainers/cli build --workspace-folder "$PWD" --image-name orca-tapo-devcontainer:base
docker build -f scripts/orca-vm/Dockerfile -t orca-tapo-devcontainer:ssh .
echo 'Image ready. Orca will copy the current Codex login into each workspace container.'
