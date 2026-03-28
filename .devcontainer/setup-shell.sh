#!/bin/bash
# Setup shell configuration for DevContainer
# This script is idempotent and can be run multiple times safely.

set -e

echo "Setting up shell configuration..."

# Function to add custom config to shell rc file
add_custom_config() {
    local rc_file=$1
    local custom_file=$2
    local marker="# DevContainer custom configuration"

    if [ ! -f "$rc_file" ]; then
        echo "⚠ $rc_file not found, skipping"
        return
    fi

    if [ ! -f "$custom_file" ]; then
        echo "⚠ $custom_file not found, skipping"
        return
    fi

    # Check if our custom section is already added
    if grep -q "$marker" "$rc_file" 2>/dev/null; then
        echo "✓ Custom configuration already present in $rc_file"
        return
    fi

    # Add custom configuration
    echo "" >> "$rc_file"
    echo "$marker" >> "$rc_file"
    echo "# Added by setup-shell.sh" >> "$rc_file"
    cat "$custom_file" >> "$rc_file"
    echo "✓ Added custom configuration to $rc_file"
}

# Setup zsh
if [ -f ".devcontainer/.zshrc" ]; then
    add_custom_config "$HOME/.zshrc" ".devcontainer/.zshrc"
fi

# Setup bash
if [ -f ".devcontainer/.bashrc" ]; then
    add_custom_config "$HOME/.bashrc" ".devcontainer/.bashrc"
fi

echo "✓ Shell configuration complete"
