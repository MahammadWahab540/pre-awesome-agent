#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-voiceagent-483614}"
LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
CREDS_PATH="${GOOGLE_APPLICATION_CREDENTIALS:-}"

# Skip credentials file check in Cloud Run - use Application Default Credentials
if [ -n "$CREDS_PATH" ] && [ ! -f "$CREDS_PATH" ]; then
  echo "WARNING: GOOGLE_APPLICATION_CREDENTIALS set but file not found at $CREDS_PATH. Using Application Default Credentials."
fi

# Try to verify Vertex AI access (non-fatal for faster startup)
python - <<'PY' || echo "WARNING: Could not verify Vertex AI access, proceeding anyway."
import os
import sys

from google.auth import default
from google.auth.transport.requests import AuthorizedSession

project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or "voiceagent-483614"
location = os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1"

try:
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    session = AuthorizedSession(creds)
    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}"
    
    response = session.get(url, timeout=5)
    if response.status_code == 403:
        print(
            f"WARNING: Service account may lack Vertex AI access for project {project_id}."
        )
        print("Grant roles/aiplatform.user to the service account if needed.")
    elif response.status_code >= 400:
        print(
            f"WARNING: Unable to verify Vertex AI permissions "
            f"(status {response.status_code})."
        )
    else:
        print(f"✅ Verified Vertex AI access for project {project_id}.")
except Exception as e:
    print(f"WARNING: Error verifying Vertex AI access: {e}")
PY

exec uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8080
