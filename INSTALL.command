#!/bin/bash
# LocalAgent Installer
# Double-click or run: bash INSTALL.command

set -e

VERSION=$(cat "$(dirname "${BASH_SOURCE[0]}")/VERSION" 2>/dev/null || echo "unknown")
echo "🔧 LocalAgent v${VERSION} Installer"
echo "================================"

# Kill any existing localagent processes
echo "⏹️  Stopping existing processes..."
pkill -9 -f "localagent" 2>/dev/null || true
pkill -9 -f "python.*9998" 2>/dev/null || true
pkill -9 -f "python.*9999" 2>/dev/null || true
lsof -ti:9998 | xargs kill -9 2>/dev/null || true
lsof -ti:9999 | xargs kill -9 2>/dev/null || true
sleep 1

# Get script directory (where zip was extracted)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Target directory
TARGET=~/localagent

# Backup old installation if exists
if [ -d "$TARGET" ]; then
    echo "📦 Backing up old installation..."
    rm -rf "${TARGET}.bak" 2>/dev/null || true
    mv "$TARGET" "${TARGET}.bak"
fi

# Copy new files
echo "📁 Installing to $TARGET..."
cp -R "$SCRIPT_DIR" "$TARGET"

# Install default skills (Anthropic SKILL.md format)
echo "🎯 Installing default skills..."
mkdir -p ~/.localagent/skills
if [ -d "$TARGET/default_skills" ]; then
    for skill_dir in "$TARGET/default_skills"/*; do
        if [ -d "$skill_dir" ] && [ -f "$skill_dir/SKILL.md" ]; then
            skill_name=$(basename "$skill_dir")
            cp -R "$skill_dir" ~/.localagent/skills/
            echo "   ✓ Installed: $skill_name"
        fi
    done
fi

# Verify
echo "✅ Installed version: $(cat $TARGET/VERSION)"

# Start server
echo "🚀 Starting LocalAgent..."
cd "$TARGET"
python3 -m localagent.service.server &

sleep 2

# Test
if curl -s http://localhost:9998/api/health | grep -q "ok"; then
    echo "✅ Server running on http://localhost:9998"
    echo "🎯 Skills directory: ~/.localagent/skills/"
    echo "   Available skills: $(ls ~/.localagent/skills/ 2>/dev/null | tr '\n' ' ')"
else
    echo "❌ Server failed to start"
fi

echo ""
echo "Done. Press any key to close."
read -n 1
