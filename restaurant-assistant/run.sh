#!/usr/bin/env bash
set -e

echo "🚀 Starting AI Restaurant Assistant..."

# Activate virtual environment
source .venv/bin/activate

# Start MCP email server in background
echo "📧 Starting MCP email server..."
python backend/mcp_email_server/server.py &
MCP_PID=$!

# Wait a moment for MCP server to start
sleep 2

# Start FastAPI backend
echo "🔧 Starting FastAPI backend..."
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Cleanup on exit
trap "kill $MCP_PID" EXIT
