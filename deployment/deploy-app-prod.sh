#!/bin/bash

# ⚠️  OUTDATED - EC2 ONLY - DO NOT USE FOR LEAPCELL
# deploy-app-prod.sh - Deploy FastAPI app for production (EC2)
# Usage: ./deploy-app-prod.sh

APP_NAME="fastapi"
APP_DIR="/home/manmehta/whisp"
VENV_DIR="/home/manmehta/whisp/venv"
#!/usr/bin/env bash
set -e

APP_NAME="whisp"
APP_DIR="/home/manmehta/whisp"
VENV_DIR="/home/manmehta/whisp/venv"
SERVICE_NAME="whisp"
GIT_BRANCH="main"
PYTHON_BIN="python3"

echo "🚀 Deploying $APP_NAME..."

cd "$APP_DIR"

echo "📥 Pulling latest code..."
git fetch origin
git checkout "$GIT_BRANCH"
git pull origin "$GIT_BRANCH"

echo "🐍 Setting up virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
  $PYTHON_BIN -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🗄️ Running database migrations..."
if [ -f "alembic.ini" ]; then
  alembic upgrade head
else
  echo "⚠️  No alembic.ini found, skipping migrations"
fi

echo "🔄 Reloading systemd + restarting app..."
systemctl daemon-reload
systemctl restart "$SERVICE_NAME"

echo "🔄 Restarting FastAPI service..."
echo "🌐 Restarting nginx..."
sudo systemctl reload nginx

echo "✅ Deployment complete!"
