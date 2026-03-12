#!/bin/bash
set -euo pipefail

# Configuration
PROJECT_ID="voiceagent-483614"
REGION="us-central1"
SERVICE_NAME="voice-agent-backend"
DB_INSTANCE="voiceagent-483614:us-central1:voiceagent-db"
DB_SOCKET_PATH="/cloudsql/${DB_INSTANCE}"
DB_USER_SECRET="${DB_USER_SECRET:-voice-agent-db-user-staging}"
DB_PASS_SECRET="${DB_PASS_SECRET:-voice-agent-db-pass-staging}"
DB_NAME_SECRET="${DB_NAME_SECRET:-voice-agent-db-name-staging}"

echo "🚀 Deploying ${SERVICE_NAME} to Cloud Run..."
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Database: ${DB_INSTANCE}"

# Deploy configuration
# - source .: Build from current directory
# - allow-unauthenticated: Required for public access
# - add-cloudsql-instances: Attaches the Cloud SQL instance
# - update-env-vars: Switches app to Cloud SQL mode and points DB_HOST to the Unix socket path
# - set-secrets: Pulls DB credentials from Secret Manager (no hardcoded secrets)

gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --session-affinity \
  --timeout 3600 \
  --add-cloudsql-instances "${DB_INSTANCE}" \
  --min-instances 1 \
  --no-cpu-throttling \
  --cpu-boost \
  --update-env-vars "^;^USE_LOCAL_DB=FALSE;USE_DB=TRUE;USE_CLOUD_SQL=TRUE;DB_HOST=${DB_SOCKET_PATH};CLOUD_SQL_CONNECTION_NAME=${DB_INSTANCE};GOOGLE_CLOUD_LOCATION=${REGION}" \
  --set-secrets "DB_USER=${DB_USER_SECRET}:latest,DB_PASS=${DB_PASS_SECRET}:latest,DB_PASSWORD=${DB_PASS_SECRET}:latest,DB_NAME=${DB_NAME_SECRET}:latest"

echo "✅ Deployment command finished."
