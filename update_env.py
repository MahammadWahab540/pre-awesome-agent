import subprocess

env_vars = "CORS_ORIGINS=http://localhost:9002,https://nxtgig.tech,https://nxtwave-voice-agent.web.app,https://nxtwave-voice-agent.firebaseapp.com,https://voice-agent-frontend-o4dv7heaia-uc.a.run.app,https://voice-agent-frontend-956365507130.us-central1.run.app"

try:
    subprocess.run([
        "gcloud.cmd", "run", "services", "update", "voice-agent-backend",
        "--update-env-vars", env_vars,
        "--region", "us-central1",
        "--project", "voiceagent-483614"
    ], check=True)
    print("Successfully updated voice-agent-backend")
except subprocess.CalledProcessError as e:
    print(f"Error updating service: {e}")
