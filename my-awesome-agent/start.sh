#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-voiceagent-483614}"
LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
CREDS_PATH="${GOOGLE_APPLICATION_CREDENTIALS:-}"

if [ -z "$CREDS_PATH" ]; then
  echo "WARNING: GOOGLE_APPLICATION_CREDENTIALS not set; relying on ADC."
else
  if [ ! -f "$CREDS_PATH" ]; then
    echo "ERROR: GOOGLE_APPLICATION_CREDENTIALS file not found at $CREDS_PATH"
    exit 1
  fi
fi

python - <<'PY'
import os
import sys

from google.auth import default
from google.auth.transport.requests import AuthorizedSession

project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or "voiceagent-483614"
location = os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1"

creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
session = AuthorizedSession(creds)
url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}"

response = session.get(url, timeout=10)
if response.status_code == 403:
    print(
        f"ERROR: Service account lacks Vertex AI access for project {project_id}."
    )
    print("Grant roles/aiplatform.user to the service account.")
    sys.exit(1)
if response.status_code >= 400:
    print(
        "ERROR: Unable to verify Vertex AI permissions "
        f"(status {response.status_code})."
    )
    print(response.text)
    sys.exit(1)

print(f"Verified Vertex AI access for project {project_id}.")
PY

exec uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8080
