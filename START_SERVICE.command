#!/bin/bash
cd "$(dirname "$0")"

echo "================================"
echo "LocalAgent Service Worker v3.0"
echo "================================"
echo ""
echo "Starting on http://localhost:9999"
echo ""

python3 -m localagent.service.server
