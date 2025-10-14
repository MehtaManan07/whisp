#!/bin/bash

# deploy-celery-dev.sh - Deploy Celery worker and beat for local development
# Usage: ./deploy-celery-dev.sh

APP_DIR="/Users/manmehta/code/personal/agentic/whisp"
VENV_DIR="/Users/manmehta/code/personal/agentic/whisp/venv"

echo "🔄 Deploying Celery services (LOCAL DEV)..."

cd $APP_DIR || exit

echo "📦 Activating virtual environment..."
source $VENV_DIR/bin/activate

echo "🛑 Stopping existing Celery processes..."
pkill -f "celery.*app.core.celery_worker" || true
sleep 2

echo "🚀 Starting Celery worker and beat..."
nohup celery -A app.core.celery_worker worker --beat --loglevel=info > /tmp/celery-dev.log 2>&1 &
CELERY_PID=$!

echo "✅ Celery started with PID: $CELERY_PID"

# Wait a moment and check if it's running
sleep 3
if ps -p $CELERY_PID > /dev/null; then
    echo "✅ Celery is running successfully"
    echo "📄 Log file: /tmp/celery-dev.log"
    echo "📋 To view logs: tail -f /tmp/celery-dev.log"
    echo "🛑 To stop: pkill -f 'celery.*app.core.celery_worker'"
else
    echo "❌ Celery failed to start"
    echo "📄 Check logs: cat /tmp/celery-dev.log"
    exit 1
fi

deactivate

echo ""
echo "✅ Local Celery deployment complete!"
echo "🔔 Reminder system is now active - checking every 2 minutes"
