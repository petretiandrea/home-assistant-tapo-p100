# Orca Dev Container recipe

This recipe starts one local Docker container per Orca workspace. It builds on
`.devcontainer/devcontainer.json`, adds SSH and Codex, and uses the repository's
`script/setup/setup` to prepare Home Assistant.

The repository-root `overlord.yaml` exposes the same recipe for Overlord.
`orca.yaml` remains available for Orca; both configurations share the scripts
in this directory. Keep their recipe definitions in sync when changing them.

One-time setup:

```sh
./scripts/orca-vm/build.sh
```

Sign in to Codex on the desktop first. The recipe copies only the desktop's
`~/.codex/auth.json` into each new container, and checks its login status.
Choose **Dev Container (Docker)** in Orca's **Run on** menu.

Docker and `npx` must be available on the desktop. The credential exists only
in each disposable container and is never built into an image. The SSH key
stays local. If desktop Codex stores credentials only in the OS keyring,
configure file-based storage before using this recipe. For Git operations
requiring GitHub authentication, configure `gh auth login` inside the container
separately.
