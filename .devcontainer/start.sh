#!/usr/bin/env bash
set -euo pipefail

action="${1:-run}"

case "$action" in
  run)
    exec bash script/develop
    ;;
  bootstrap)
    exec bash script/setup/bootstrap
    ;;
  *)
    echo "Usage: $0 [run|bootstrap]"
    exit 1
    ;;
esac
