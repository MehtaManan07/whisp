#!/bin/bash

ENV=$1
URL=$2

# Load environment variables from .env file
if [ ! -f .env ]; then
  echo "Error: .env file not found!"
  exit 1
fi

# Export variables from .env file
export $(grep -v '^#' .env | grep -E 'WA_APP_ID|WA_APP_SECRET|WA_VERIFY_TOKEN' | xargs)

# Check if required variables are set
if [ -z "$WA_APP_ID" ] || [ -z "$WA_APP_SECRET" ] || [ -z "$WA_VERIFY_TOKEN" ]; then
  echo "Error: Required environment variables not found in .env file"
  echo "Please ensure WA_APP_ID, WA_APP_SECRET, and WA_VERIFY_TOKEN are set"
  exit 1
fi

if [ "$ENV" = "dev" ]; then
  WEBHOOK_URL=$URL
elif [ "$ENV" = "prod" ]; then
  WEBHOOK_URL="https://whisp-ai.duckdns.org"
else
  echo "Usage: $0 [dev|prod]"
  exit 1
fi

echo "🔧 Setting up WhatsApp webhook for $ENV environment..."
echo "📍 Webhook URL: $WEBHOOK_URL/whatsapp/webhook"
echo "🔑 Using App ID: $WA_APP_ID"

# Fetch app access token using client credentials
echo "🔐 Fetching app access token..."
TOKEN_RESPONSE=$(curl -s -X GET "https://graph.facebook.com/oauth/access_token?client_id=$WA_APP_ID&client_secret=$WA_APP_SECRET&grant_type=client_credentials")

# Extract access token from JSON response
APP_ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$APP_ACCESS_TOKEN" ]; then
  echo "❌ Failed to fetch app access token"
  echo "Response: $TOKEN_RESPONSE"
  exit 1
fi

echo "✅ App access token fetched successfully" $APP_ACCESS_TOKEN
echo ""

# Set up webhook subscription
echo "📡 Configuring webhook subscription..."
curl -X POST "https://graph.facebook.com/v19.0/$WA_APP_ID/subscriptions" \
  -H "Authorization: Bearer $APP_ACCESS_TOKEN" \
  -F "object=whatsapp_business_account" \
  -F "callback_url=$WEBHOOK_URL/whatsapp/webhook" \
  -F "fields=messages" \
  -F "verify_token=$WA_VERIFY_TOKEN"

echo ""
echo "✅ Webhook setup request completed!"
