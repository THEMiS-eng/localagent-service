#!/bin/bash

# GitHub Repositories Creation Script for LocalAgent Service
# Version: 3.3.015

set -e

ORG="THEMiS-eng"
BASE_NAME="localagent"

# Array of module names
MODULES=(
    "core"
    "ui"
    "api"
    "websocket"
    "file-manager"
    "process-monitor"
    "network-tools"
    "security"
    "docker"
    "git"
    "database"
    "cloud"
)

echo "Creating GitHub repositories for LocalAgent Service modules..."
echo "Organization: $ORG"
echo "Base name: $BASE_NAME"
echo "Modules to create: ${#MODULES[@]}"

for module in "${MODULES[@]}"; do
    REPO_NAME="${BASE_NAME}-${module}"
    echo "\nCreating repository: $REPO_NAME"
    
    # Create repository
    gh repo create "$ORG/$REPO_NAME" \
        --description "LocalAgent Service - $module module" \
        --private \
        --clone=false
    
    if [ $? -eq 0 ]; then
        echo "✓ Repository $REPO_NAME created successfully"
    else
        echo "✗ Failed to create repository $REPO_NAME"
    fi
done

echo "\n✓ Repository creation completed!"
echo "Next steps:"
echo "1. Clone repositories locally"
echo "2. Add initial project structure"
echo "3. Configure CI/CD pipelines"