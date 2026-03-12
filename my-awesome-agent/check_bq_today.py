import subprocess
import json

def run_bq_query():
    query = """
    SELECT 
        input_transcription, 
        output_transcription, 
        timestamp, 
        session_id 
    FROM `nxtwave-voice-agent.adk_sessions_staging.events` 
    WHERE timestamp >= '2026-03-12 00:00:00' 
    ORDER BY timestamp DESC 
    LIMIT 10
    """
    cmd = [
        "bq", "query", 
        "--use_legacy_sql=false", 
        "--format=json",
        query
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return
    
    try:
        events = json.loads(result.stdout)
        if not events:
            print("No events found today.")
            return
        for e in events:
            print(f"[{e['timestamp']}] Session: {e['session_id']}")
            print(f"  User: {e['input_transcription']}")
            print(f"  Agent: {e['output_transcription']}")
            print("-" * 20)
    except Exception as ex:
        print(f"Parse error: {ex}")
        print(f"Stdout: {result.stdout[:500]}")

if __name__ == "__main__":
    run_bq_query()
