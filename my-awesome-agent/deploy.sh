#!/bin/bash

# Configuration
PROJECT_ID="voiceagent-483614"
REGION="us-central1"
SERVICE_NAME="voice-agent-backend"
DB_INSTANCE="voiceagent-483614:us-central1:voiceagent-db"
DB_SOCKET_PATH="/cloudsql/${DB_INSTANCE}"

echo "🚀 Deploying ${SERVICE_NAME} to Cloud Run..."
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Database: ${DB_INSTANCE}"

# Deploy configuration
# - source .: Build from current directory
# - allow-unauthenticated: Required for public access
# - add-cloudsql-instances: Attaches the Cloud SQL instance
# - update-env-vars: Sets DB_HOST to the Unix socket path

gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --add-cloudsql-instances "${DB_INSTANCE}" \
  --update-env-vars "^:^DB_HOST=${DB_SOCKET_PATH}"

echo "✅ Deployment command finished."
