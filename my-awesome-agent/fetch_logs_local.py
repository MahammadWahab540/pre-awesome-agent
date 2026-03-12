import subprocess
import json
import os

def run_gcloud_logs():
    # Search for ANY cloud run revision logs in this project from today.
    filter_str = 'resource.type="cloud_run_revision" AND timestamp>="2026-03-12T04:30:00Z"'
    cmd = [
        "gcloud", "logging", "read", filter_str,
        "--limit", "50",
        "--project", "voiceagent-483614",
        "--format", "json"
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return
    
    try:
        logs = json.loads(result.stdout)
        if not logs:
            print("No logs found since 04:30 UTC.")
            return
        for log in logs:
            ts = log.get('timestamp')
            svc = log.get('resource', {}).get('labels', {}).get('service_name')
            payload = log.get('textPayload', '')
            print(f"{ts} | {svc} | {payload[:100]}...")
    except Exception as e:
        print(f"Parse error: {e}")
        print(f"Stdout: {result.stdout[:500]}")

if __name__ == "__main__":
    run_gcloud_logs()
