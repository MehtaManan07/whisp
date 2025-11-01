#!/bin/bash

# ⚠️  OUTDATED - EC2 ONLY - DO NOT USE FOR LEAPCELL
# deploy-celery-prod.sh - Deploy Celery services for production (EC2)
# Usage: ./deploy-celery-prod.sh

APP_DIR="/home/ec2-user/whisp"
VENV_DIR="/home/ec2-user/whisp/venv"

echo "🔄 Deploying Celery services (PRODUCTION - EC2)..."

cd $APP_DIR || exit

echo "📦 Activating virtual environment..."
source $VENV_DIR/bin/activate

echo "🔍 Checking if systemd services exist..."
if systemctl list-unit-files | grep -q "celery-worker.service"; then
    echo "📋 Using systemd services..."
    
    echo "🔄 Restarting Celery worker..."
    sudo systemctl restart celery-worker
    
    echo "🔄 Restarting Celery beat..."
    sudo systemctl restart celery-beat
    
    echo "✅ Checking service status..."
    if systemctl is-active --quiet celery-worker && systemctl is-active --quiet celery-beat; then
        echo "✅ All Celery services are running"
    else
        echo "❌ Some Celery services failed to start"
        sudo systemctl status celery-worker --no-pager
        sudo systemctl status celery-beat --no-pager
        exit 1
    fi
    
    echo "📄 Recent worker logs:"
    sudo journalctl -u celery-worker -n 5 --no-pager
    
    echo "📄 Recent beat logs:"
    sudo journalctl -u celery-beat -n 5 --no-pager
    
else
    echo "📋 No systemd services found, using manual start..."
    
    echo "🛑 Stopping existing Celery processes..."
    pkill -f "celery.*app.core.celery_worker" || true
    sleep 2
    
    echo "🚀 Starting Celery worker..."
    nohup celery -A app.core.celery_worker worker --loglevel=info --pidfile=/tmp/celery-worker.pid --detach
    
    echo "🚀 Starting Celery beat..."
    nohup celery -A app.core.celery_worker beat --loglevel=info --pidfile=/tmp/celery-beat.pid --detach
    
    sleep 3
    
    if pgrep -f "celery.*worker" > /dev/null && pgrep -f "celery.*beat" > /dev/null; then
        echo "✅ Celery services started successfully"
    else
        echo "❌ Failed to start Celery services"
        exit 1
    fi
fi

deactivate

echo ""
echo "✅ Production Celery deployment complete!"
echo "🔔 Reminder system is now active - checking every 2 minutes"
echo ""
echo "📋 Management commands:"
echo "  systemctl status celery-worker celery-beat"
echo "  journalctl -u celery-worker -f"
echo "  journalctl -u celery-beat -f"
