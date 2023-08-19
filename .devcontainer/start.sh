#!/usr/bin/env bash

function workspacePath {
    if [[ -n "$WORKSPACE_DIRECTORY" ]]; then
        echo "${WORKSPACE_DIRECTORY}/"
    else
        echo "$(find /workspaces -mindepth 1 -maxdepth 1 -type d | tail -1)/"
    fi
}

action="$1"  # Get the first argument passed to the script

if [[ "$action" == "setversion" ]]; then
    read -p "Enter Home Assistant version: " version
    echo "Installing Home Assistant version $version"
    pip install "homeassistant==$version"
elif [[ "$action" == "run" ]]; then
    mkdir -p /tmp/config/custom_components

    if test -f ".devcontainer/configuration.yaml"; then
        echo "Copy configuration.yaml"
        ln -sf "$(workspacePath).devcontainer/configuration.yaml" /tmp/config/configuration.yaml || echo ".devcontainer/configuration.yaml is missing"
    fi

    if test -d "custom_components"; then
        echo "Symlink the custom component directory"

        if test -d "custom_components"; then
            rm -R /tmp/config/custom_components
        fi

        ln -sf "$(workspacePath)custom_components/" /tmp/config/custom_components || { echo "Could not symlink the custom_component"; exit 1; }
    elif  test -f "__init__.py"; then
        echo "Having the component in the root is currently not supported"
    fi

    echo "Start Home Assistant"
    hass --script ensure_config -c /tmp/config
    hass -c /tmp/config
else
    echo "Unknown action: $action"
    echo "Usage: $0 [run|setversion <version>]"
    exit 1
fi
