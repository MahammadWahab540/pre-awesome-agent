import json
import subprocess

with open('backend_info.json', 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

env_array = data['spec']['template']['spec']['containers'][0].get('env', [])

with open('env_vars.yaml', 'w', encoding='utf-8') as f:
    for e in env_array:
        key = e['name']
        val = e['value']
        if key == 'CORS_ORIGINS':
            continue
        # simple escaping for yaml
        f.write(f"{key}: '{val}'\n")
    
    cors = "http://localhost:9002,https://nxtgig.tech,https://nxtwave-voice-agent.web.app,https://nxtwave-voice-agent.firebaseapp.com,https://voice-agent-frontend-o4dv7heaia-uc.a.run.app,https://voice-agent-frontend-956365507130.us-central1.run.app,https://voice-agent-frontend-o4dv7heaia-uc.a.run.app"
    f.write(f"CORS_ORIGINS: '{cors}'\n")

try:
    subprocess.run([
        "gcloud.cmd", "run", "services", "update", "voice-agent-backend",
        "--env-vars-file", "env_vars.yaml",
        "--region", "us-central1",
        "--project", "voiceagent-483614"
    ], check=True)
    print("Successfully updated voice-agent-backend")
except subprocess.CalledProcessError as e:
    print(f"Error updating service {e}")
