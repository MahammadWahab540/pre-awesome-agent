
import os
import re

# 1. Patch SequentialAgent.py
lib_path = '.venv/lib/python3.11/site-packages/google/adk/agents/sequential_agent.py'
if os.path.exists(lib_path):
    with open(lib_path, 'r') as f:
        content = f.read()
    
    # State loading fix
    state_load_pattern = r'agent_state = self\._load_agent_state\(ctx, SequentialAgentState\)\s+start_index = self\._get_start_index\(agent_state\)'
    state_load_fix = """
    # Initialize or resume the execution state from the agent state.
    agent_state = self._load_agent_state(ctx, SequentialAgentState)
    # FALLBACK: If current invocation has no state, search previous invocations in history
    if agent_state is None and ctx.session and ctx.session.events:
        for event in reversed(ctx.session.events):
            if event.author == self.name and event.actions.agent_state:
                try:
                    from .sequential_agent import SequentialAgentState
                    agent_state = SequentialAgentState.model_validate(event.actions.agent_state)
                    logger.info(f"📍 Resuming {self.name} from historical state: {agent_state.current_sub_agent}")
                    break
                except Exception:
                    continue

    start_index = self._get_start_index(agent_state)
"""
    if 'history-aware state loading' not in content:
        content = re.sub(state_load_pattern, state_load_fix, content)

    # Task completed fix
    if 'def task_completed(tool_context: ToolContext):' not in content:
        old_tc = 'def task_completed():\n      """\n      Signals that the agent has successfully completed the user\'s question\n      or task.\n      """\n      return \'Task completion signaled.\''
        new_tc = 'def task_completed(tool_context: ToolContext):\n      """\n      Signals that the agent has successfully completed the user\'s question\n      or task.\n      """\n      if tool_context.state.get("is_resuming"):\n        return "IGNORING completion signal because we are in resumption mode. Please speak to the user first."\n      return "Task completion signaled."'
        content = content.replace(old_tc, new_tc)

    # Imports fix
    if 'from google.adk.tools import ToolContext' not in content:
        content = content.replace('from __future__ import annotations', 'from __future__ import annotations\nfrom google.adk.tools import ToolContext')
    
    # Fix the literal \n if it exists
    content = content.replace('\\n# Copyright', '\n# Copyright')
    content = content.replace('ToolContext\\n', 'ToolContext\n')

    with open(lib_path, 'w') as f:
        f.write(content)
    print("SequentialAgent.py patched.")

# 2. Patch fast_api_app.py
app_path = 'app/fast_api_app.py'
if os.path.exists(app_path):
    with open(app_path, 'r') as f:
        content = f.read()
    
    # Improved append_event with duplicate check
    append_fix = """
                    # Persist only NEW events
                    try:
                        if not any(e.id == event.id for e in session.events):
                            await session_service.append_event(session, event)
                    except Exception as e:
                        if "Duplicate entry" not in str(e):
                            logger.error(f"Failed to append event to session: {e}")
"""
    # Replace the old try block
    content = re.sub(r'try:\s+await session_service\.append_event\(session, event\)\s+except Exception as e:\s+logger\.error\(f"Failed to append event to session: \{e\}"\)', append_fix, content)

    if 'self.session = session' not in content:
        content = content.replace('session = await session_service.create_session(', 'self.session = await session_service.create_session(', 1)
        content = content.replace('self.session_id = session.id', 'self.session_id = self.session.id', 1)

    with open(app_path, 'w') as f:
        f.write(content)
    print("fast_api_app.py patched.")

# 3. Clean tools.py
tools_path = 'app/agents/tools.py'
if os.path.exists(tools_path):
    with open(tools_path, 'r') as f:
        content = f.read()
    content = content.replace('\\"\\"\\"', '"""')
    with open(tools_path, 'w') as f:
        f.write(content)
    print("tools.py cleaned.")
