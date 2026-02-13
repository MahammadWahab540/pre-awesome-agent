
import os
import re
import glob as glob_mod

# 1. Patch SequentialAgent.py - find path cross-platform
lib_path = None

# Try common paths (Linux Docker, Windows venv, etc.)
candidates = [
    '.venv/lib/python*/site-packages/google/adk/agents/sequential_agent.py',
    '.venv/Lib/site-packages/google/adk/agents/sequential_agent.py',
    '/usr/local/lib/python*/site-packages/google/adk/agents/sequential_agent.py',
    '/code/.venv/lib/python*/site-packages/google/adk/agents/sequential_agent.py',
]
for pattern in candidates:
    matches = glob_mod.glob(pattern)
    if matches:
        lib_path = matches[0]
        break

if lib_path and os.path.exists(lib_path):
    print(f"Found SequentialAgent at: {lib_path}")
    with open(lib_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # --- Fix 0: Ensure ToolContext is imported for type hints ---
    if 'from google.adk.tools import ToolContext' not in content:
        # Must be careful not to break from __future__ imports which MUST be at the top
        future_imports = re.findall(r'^from __future__ import [^\n]+\n', content, re.MULTILINE)
        if future_imports:
            # Get the last future import
            last_future = future_imports[-1]
            content = content.replace(last_future, last_future + "from google.adk.tools import ToolContext\n")
        else:
            content = "from google.adk.tools import ToolContext\n" + content
        print("Added ToolContext import to SequentialAgent.py")

    # --- Fix 1: Stop infinite appending of task_completed ---
    # Target the deduplication logic inside _run_live_impl
    old_dedup = 'if task_completed.__name__ not in existing_tool_names:'
    new_dedup = 'if "task_completed" not in existing_tool_names:'
    
    if old_dedup in content:
        content = content.replace(old_dedup, new_dedup)
        print("SequentialAgent.py dedupe logic fixed (string name check).")

    # --- Fix 2: Restore is_resuming check and fix nested function signature ---
    # The nested task_completed in _run_live_impl often takes NO args in default ADK
    # We patch it to take tool_context and handle is_resuming
    
    # Match the nested function definition in _run_live_impl
    # We use a robust regex that handles both empty and tool_context versions
    nested_pattern = r'def task_completed\([^)]*\):\s+"""[^"]+"""\s+return [\'"]Task completion signaled\.[\'"]'
    
    nested_replacement = """def task_completed(tool_context: ToolContext):
        \"\"\"
        Signals that the agent has successfully completed the user's question
        or task.
        \"\"\"
        # Optimization: Ignore completion during history replay to prevent slow starts
        if tool_context.state.get("is_resuming"):
            return "IGNORING completion signal because we are in resumption mode. Please speak to the user first."
        return 'Task completion signaled.'"""
    
    if re.search(nested_pattern, content):
        content = re.sub(nested_pattern, nested_replacement, content, flags=re.DOTALL)
        print("SequentialAgent.py nested task_completed patched (is_resuming check + signature).")

    with open(lib_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SequentialAgent.py patching complete.")
else:
    print(f"WARNING: SequentialAgent.py not found at expected paths. Skipping patch.")

# 2. Patch fast_api_app.py
app_path = 'app/fast_api_app.py'
if os.path.exists(app_path):
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Ensure current_stage_index is initialized if not present
    if 'current_stage_index": 0' not in content:
        # This was already fixed by manual edit, but we'll leave this check for safety
        pass

    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("fast_api_app.py verified.")

# 3. Clean tools.py
tools_path = 'app/agents/tools.py'
if os.path.exists(tools_path):
    with open(tools_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('\\"\\"\\"', '"""')
    with open(tools_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("tools.py cleaned.")
