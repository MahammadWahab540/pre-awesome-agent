#!/bin/bash

# Deploy my-awesome-agent Backend to Google Cloud Run
# This script builds and deploys the FastAPI-based chat agent backend

set -e  # Exit on error

echo "🚀 Deploying my-awesome-agent Backend to Cloud Run..."
echo ""

# Configuration
PROJECT_ID="studio-811179716-d5a1f"
SERVICE_NAME="my-awesome-agent"
REGION="asia-south1"
MEMORY="1Gi"
CPU="1"
TIMEOUT="300"
MAX_INSTANCES="10"
MIN_INSTANCES="0"

# Cloud SQL Connection
INSTANCE_CONNECTION_NAME="kossip-helpers-270615:asia-south1:dev-query"

# Cloud SQL Database Credentials (from fast_api_app.py)
DB_USER="${DB_USER:-adk_sessions_user}"
DB_PASSWORD="${DB_PASSWORD:-(;G*&ftrQ}Bd(\"iQ}"
DB_NAME="${DB_NAME:-adk_sessions}"

# CORS Origins (for production)
CORS_ORIGINS="${CORS_ORIGINS:-https://nxtgig.tech,https://*.nxtgig.tech,https://studio-811179716-d5a1f.web.app,https://studio-811179716-d5a1f.firebaseapp.com}"

# Flask Configuration (if needed)
FLASK_ENV="${FLASK_ENV:-development}"
PORT="${PORT:-5000}"

# Service Account (REQUIRED: Custom service account for Cloud Run)
SERVICE_ACCOUNT="clourun-aiaccelerator@studio-811179716-d5a1f.iam.gserviceaccount.com"

# Service account key secret (optional if using Cloud Run default credentials)
GOOGLE_APPLICATION_CREDENTIALS_PATH="${GOOGLE_APPLICATION_CREDENTIALS_PATH:-/var/secrets/google/service-account.json}"
GOOGLE_APPLICATION_CREDENTIALS_SECRET="${GOOGLE_APPLICATION_CREDENTIALS_SECRET:-}"

# Environment Variables (REQUIRED: Set these before deploying)
# TODO: Set your Vertex AI Memory Bank ID (Agent Engine ID)
# Get this from: https://console.cloud.google.com/gen-app-builder/engines
AGENT_ENGINE_ID="${AGENT_ENGINE_ID:-}"  # Set via: export AGENT_ENGINE_ID="your-engine-id"

# Optional: GCS bucket for artifact/log storage
LOGS_BUCKET_NAME="${LOGS_BUCKET_NAME:-}"  # Set via: export LOGS_BUCKET_NAME="gs://your-bucket"

# Gemini Model Name (can be changed without redeployment)
GEMINI_MODEL_NAME="${GEMINI_MODEL_NAME:-gemini-live-2.5-flash-preview-native-audio-09-2025}"

# Get directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" > /dev/null 2>&1; then
    echo "❌ Not authenticated with gcloud. Please run: gcloud auth login"
    exit 1
fi

# Set project
echo "📋 Setting project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Get Google API Key and other variables from .env
if [ -f "$SCRIPT_DIR/app/.env" ]; then
    echo "📄 Loading environment variables from app/.env"
    source "$SCRIPT_DIR/app/.env"
elif [ -f "$SCRIPT_DIR/.env" ]; then
    echo "📄 Loading environment variables from .env"
    source "$SCRIPT_DIR/.env"
else
    echo "⚠️  No .env file found in app/ or root directory"
fi

# Note: We don't strictly enforce GOOGLE_API_KEY check here if using Vertex AI, 
# but it's good practice so the script doesn't fail silently if it's expected.
# Uncomment below if you want to enforce it.
# if [ -z "$GOOGLE_API_KEY" ]; then
#     echo "⚠️  GOOGLE_API_KEY not found in .env file. Proceeding without it (assuming Vertex AI ADC)."
# fi

# Validate required environment variables
if [ -z "$AGENT_ENGINE_ID" ]; then
    echo "⚠️  WARNING: AGENT_ENGINE_ID not set. Memory will not persist across restarts."
    echo "   To fix: export AGENT_ENGINE_ID=\"your-agent-engine-id\""
    echo "   Get your Agent Engine ID from: https://console.cloud.google.com/gen-app-builder/engines"
    echo ""
    read -p "Continue without AGENT_ENGINE_ID? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "📦 Building and deploying to Cloud Run..."
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION (Cloud Run location)"
echo "   Vertex AI Location: us-central1 (forced in code)"
echo "   Service Account: $SERVICE_ACCOUNT"
echo "   Memory: $MEMORY"
echo "   CPU: $CPU"
echo "   Agent Engine ID: ${AGENT_ENGINE_ID:-'NOT SET'}"
echo "   Gemini Model: $GEMINI_MODEL_NAME"
echo "   Credentials Path: $GOOGLE_APPLICATION_CREDENTIALS_PATH"
echo ""

echo ""

# Optional: mount service account key as a secret volume
SECRET_FLAG=""
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS_SECRET" ]; then
    SECRET_SPEC="$GOOGLE_APPLICATION_CREDENTIALS_SECRET"
    if [[ "$SECRET_SPEC" != *:* ]]; then
        SECRET_SPEC="${SECRET_SPEC}:latest"
    fi
    SECRET_FLAG="--set-secrets ${GOOGLE_APPLICATION_CREDENTIALS_PATH}=${SECRET_SPEC}"
else
    echo "⚠️  GOOGLE_APPLICATION_CREDENTIALS_SECRET not set; relying on Cloud Run ADC."
fi

# Deploy to Cloud Run with environment variables
# Note: Some env vars (CORS_ORIGINS, FIREBASE_*) are loaded from .env during build
# Only setting runtime-critical env vars here to avoid parsing issues with special characters
gcloud run deploy $SERVICE_NAME \
    --source "$SCRIPT_DIR" \
    --region $REGION \
    --platform managed \
    --service-account $SERVICE_ACCOUNT \
    --allow-unauthenticated \
    --memory $MEMORY \
    --cpu $CPU \
    --timeout $TIMEOUT \
    --max-instances $MAX_INSTANCES \
    --min-instances $MIN_INSTANCES \
    --add-cloudsql-instances $INSTANCE_CONNECTION_NAME \
    $SECRET_FLAG \
    --update-env-vars USE_LOCAL_DB=false,GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS_PATH,GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_REGION=us-central1,GOOGLE_CLOUD_LOCATION=us-central1,ENABLE_CONTEXT_COMPRESSION=true,ENABLE_PROACTIVITY=true,ENABLE_AFFECTIVE_DIALOG=true,ENABLE_CFC=true,ENABLE_AUDIO_PERSISTENCE=false,CLOUD_SQL_CONNECTION_NAME=$INSTANCE_CONNECTION_NAME,DB_USER=$DB_USER,DB_NAME=$DB_NAME,AGENT_ENGINE_ID=${AGENT_ENGINE_ID},GEMINI_MODEL_NAME=${GEMINI_MODEL_NAME}

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')

echo ""
echo "✅ Deployment successful!"
echo ""
echo "📍 Service URL: $SERVICE_URL"
echo ""
echo "🔍 Test the deployment:"
echo "   Health check: curl $SERVICE_URL/health"
echo "   Chat endpoint: POST $SERVICE_URL/api/chat"
echo ""
