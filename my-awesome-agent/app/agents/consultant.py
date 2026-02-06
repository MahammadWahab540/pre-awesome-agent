import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

# Ensure environment variables are loaded
load_dotenv(Path(__file__).parent.parent / ".env")

# Import tool functions for stage completion
from .tools import (
    complete_program_explanation,
    complete_payment_structure
)

# Read model name from environment variable, fallback to native-audio for speed
MODEL_NAME = os.getenv(
    "GEMINI_MODEL_NAME",
    "gemini-live-2.5-flash-native-audio"  # Faster native audio model as default
) 

# Paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config" / "stages_config.json"
INSTRUCTIONS_DIR = BASE_DIR / "instructions"

# Load stages config
with open(CONFIG_PATH, "r") as f:
    STAGES_CONFIG = json.load(f)

# Tools mapping
TOOLS_MAP = {
    "complete_program_explanation": FunctionTool(complete_program_explanation),
    "complete_payment_structure": FunctionTool(complete_payment_structure)
}

preload_memory_tool = PreloadMemoryTool()


def create_dynamic_instruction(base_instruction: str):
    """
    Factory function to create a dynamic instruction callable.
    This properly captures base_instruction by value, avoiding closure bugs.
    The callable receives ReadonlyContext and returns the instruction string.
    """
    def instruction_callable(context) -> str:
        # Extract user context from state
        user_name = context.state.get("user_name") or "Student"
        user_language = context.state.get("user_language") or "English"

        context_prefix = f"""
# USER CONTEXT (CRITICAL - MUST FOLLOW)
- **User Name:** {user_name}
- **Preferred Language:** {user_language}

# LANGUAGE RULES (MANDATORY)
1. **Always** address the user by their name: "{user_name}".
2. **Always** speak in {user_language}.
   - If {user_language} is Hindi, Telugu, Tamil, or any Indic language, speak in that language with 70% regional + 30% English for technical terms.
   - Technical terms like EMI, KYC, NBFC, loan, payment should remain in English.
3. Even if the instructions below are in English, your SPOKEN OUTPUT must be in {user_language}.
4. Do NOT randomly make up names. The user's name is "{user_name}" - use only this name.

---
"""
        return context_prefix + base_instruction
    return instruction_callable


# Create sub-agents dynamically
sub_agents = []
for stage in STAGES_CONFIG:
    instruction_path = INSTRUCTIONS_DIR / stage["instruction_file"]
    base_instruction = instruction_path.read_text(encoding="utf-8")

    # Use a callable for instruction to inject user context dynamically
    # ADK's LlmAgent supports callable instructions that receive context
    dynamic_instruction = create_dynamic_instruction(base_instruction)

    agent = LlmAgent(
        name=f"stage_{stage['id']}_agent",
        model=MODEL_NAME,
        instruction=dynamic_instruction,  # Pass callable instead of static string
        description=stage["description"],
        output_key=f"stage_{stage['id']}_output",
        tools=[preload_memory_tool, TOOLS_MAP[stage["tool_name"]]]
    )

    sub_agents.append(agent)

consultant_agent = SequentialAgent(
    name="ProgramRegistrationOrchestrator",
    description="Orchestrates the program registration and payment flow.",
    sub_agents=sub_agents
)
