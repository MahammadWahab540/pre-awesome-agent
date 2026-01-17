#!/bin/bash

# Quick Update Script for Gemini Model Name
# This updates ONLY the environment variable without rebuilding the container
# Automatically reads from app/.env file

set -e

echo "🔄 Updating Gemini Model Name in Production..."
echo ""

# Configuration
PROJECT_ID="studio-811179716-d5a1f"
SERVICE_NAME="my-awesome-agent"
REGION="asia-south1"

# Get directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Try to read model name from .env file first
NEW_MODEL_NAME=""

if [ -f "$SCRIPT_DIR/app/.env" ]; then
    echo "📄 Reading GEMINI_MODEL_NAME from app/.env..."
    # Extract GEMINI_MODEL_NAME from .env file (handles comments and various formats)
    NEW_MODEL_NAME=$(grep -E "^GEMINI_MODEL_NAME=" "$SCRIPT_DIR/app/.env" | cut -d '=' -f2- | tr -d '"' | tr -d "'" | xargs)
fi

# If not found in .env, check command line argument
if [ -z "$NEW_MODEL_NAME" ] && [ -n "$1" ]; then
    NEW_MODEL_NAME="$1"
    echo "📄 Using model name from command line argument"
fi

# If still not found, show error
if [ -z "$NEW_MODEL_NAME" ]; then
    echo "❌ Error: GEMINI_MODEL_NAME not found in app/.env and no argument provided"
    echo ""
    echo "Usage Option 1 (Recommended): Add to app/.env file:"
    echo "  GEMINI_MODEL_NAME=your-model-name"
    echo "  Then run: ./update-model.sh"
    echo ""
    echo "Usage Option 2: Pass as argument:"
    echo "  ./update-model.sh <model-name>"
    echo ""
    echo "Available models:"
    echo "  - gemini-live-2.5-flash-preview-native-audio-09-2025 (default)"
    echo "  - gemini-live-2.5-flash-native-audio"
    echo "  - gemini-2.5-flash-native-audio-preview-09-2025"
    exit 1
fi

# Set project
echo ""
gcloud config set project $PROJECT_ID

echo ""
echo "📝 Update Configuration:"
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION"
echo "   New Model: $NEW_MODEL_NAME"
echo ""

read -p "Continue with update? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Update cancelled"
    exit 1
fi

# Update only the GEMINI_MODEL_NAME environment variable
gcloud run services update $SERVICE_NAME \
    --region $REGION \
    --update-env-vars GEMINI_MODEL_NAME=$NEW_MODEL_NAME

echo ""
echo "✅ Model name updated successfully!"
echo ""
echo "🔍 Verify the change:"
echo "   gcloud run services describe $SERVICE_NAME --region $REGION --format='value(spec.template.spec.containers[0].env)'"
echo ""
echo "⚡ The change takes effect immediately - no container rebuild needed!"
echo ""

