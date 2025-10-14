#!/bin/bash

# deploy-app-dev.sh - Deploy FastAPI app for local development
# Usage: ./deploy-app-dev.sh

APP_DIR="/Users/manmehta/code/personal/agentic/whisp"
VENV_DIR="/Users/manmehta/code/personal/agentic/whisp/venv"

echo "🚀 Deploying FastAPI app (LOCAL DEV)..."

echo "📦 Installing dependencies..."
cd $APP_DIR || exit
source $VENV_DIR/bin/activate
pip install -r requirements.txt

echo "🔄 Restarting FastAPI server..."
# Kill existing uvicorn process if running
pkill -f "uvicorn.*main:app" || true
sleep 2

echo "🚀 Starting FastAPI server..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/fastapi-dev.log 2>&1 &
FASTAPI_PID=$!

# Wait a moment and check if it's running
sleep 3
if ps -p $FASTAPI_PID > /dev/null; then
    echo "✅ FastAPI is running on http://localhost:8000 (PID: $FASTAPI_PID)"
    echo "📄 Log file: /tmp/fastapi-dev.log"
    echo "📋 To view logs: tail -f /tmp/fastapi-dev.log"
    echo "🛑 To stop: pkill -f 'uvicorn.*main:app'"
else
    echo "❌ FastAPI failed to start"
    echo "📄 Check logs: cat /tmp/fastapi-dev.log"
    exit 1
fi

deactivate

echo ""
echo "✅ Local development deployment complete!"
