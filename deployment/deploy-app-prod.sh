#!/bin/bash

# deploy-app-prod.sh - Deploy FastAPI app for production (EC2)
# Usage: ./deploy-app-prod.sh

APP_NAME="fastapi"
APP_DIR="/home/ec2-user/whisp"
VENV_DIR="/home/ec2-user/whisp/venv"

echo "🚀 Deploying FastAPI app (PRODUCTION - EC2)..."

echo "📥 Pulling latest changes..."
cd $APP_DIR || exit
git pull origin main

echo "📦 Installing dependencies..."
source $VENV_DIR/bin/activate
pip install -r requirements.txt

echo "🔄 Restarting FastAPI service..."
sudo systemctl restart $APP_NAME

echo "🌐 Restarting nginx..."
sudo systemctl reload nginx

echo "✅ Checking service status..."
if sudo systemctl is-active --quiet $APP_NAME; then
    echo "✅ FastAPI service is running"
else
    echo "❌ FastAPI service failed to start"
    sudo systemctl status $APP_NAME --no-pager
    exit 1
fi

echo "📄 Recent logs:"
sudo journalctl -u $APP_NAME -n 10 --no-pager

echo ""
echo "✅ Production deployment complete!"
