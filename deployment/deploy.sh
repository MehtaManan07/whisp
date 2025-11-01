#!/bin/bash

# ⚠️  OUTDATED - EC2 ONLY - DO NOT USE FOR LEAPCELL
# deploy.sh
# Usage: ./deploy.sh

APP_NAME="fastapi"       # systemd service name
APP_DIR="/home/ec2-user/whisp"  # path to your app repo
VENV_DIR="/home/ec2-user/whisp/venv" # optional, if using virtualenv

echo "Pulling latest changes..."
cd $APP_DIR || exit
git pull origin main

echo "Installing dependencies..."
# If using virtualenv
source $VENV_DIR/bin/activate
pip install -r requirements.txt
deactivate

echo "Restarting service..."
sudo systemctl restart $APP_NAME

echo "Restarting ngnix..."
sudo systemctl reload nginx

echo "Checking service status..."
sudo systemctl status $APP_NAME --no-pager

echo "Done! Logs (last 10 lines):"
sudo journalctl -u $APP_NAME -n 10 --no-pager
