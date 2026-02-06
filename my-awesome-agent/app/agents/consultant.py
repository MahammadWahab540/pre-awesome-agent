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


def validate_stage_config():
    """
    Validates that all stage configuration is correct before creating agents.
    Prevents runtime crashes from missing instruction files or invalid tool references.
    
    Raises:
        ValueError: If validation problems are found (missing files or invalid tool names).
                   All validation errors are aggregated and reported together.
    """
    errors = []
    
    for stage in STAGES_CONFIG:
        stage_id = stage.get('id', 'unknown')
        
        # Check instruction file exists
        instruction_file = stage.get('instruction_file')
        if not instruction_file:
            errors.append(f"Stage {stage_id}: Missing 'instruction_file' in config")
        else:
            instruction_path = INSTRUCTIONS_DIR / instruction_file
            if not instruction_path.exists():
                errors.append(f"Stage {stage_id}: Instruction file not found: {instruction_path}")
            elif not instruction_path.is_file():
                errors.append(f"Stage {stage_id}: Instruction path is not a file: {instruction_path}")
        
        # Check tool exists in TOOLS_MAP
        tool_name = stage.get('tool_name')
        if not tool_name:
            errors.append(f"Stage {stage_id}: Missing 'tool_name' in config")
        elif tool_name not in TOOLS_MAP:
            errors.append(f"Stage {stage_id}: Tool '{tool_name}' not found in TOOLS_MAP. Available tools: {list(TOOLS_MAP.keys())}")
    
    if errors:
        error_message = "\n❌ Stage configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
        raise ValueError(error_message)
    
    print("✅ Stage configuration validated successfully")


def create_dynamic_instruction(base_instruction: str):
    """
    Creates a string template with placeholders for user context.
    ADK's LlmAgent automatically resolves {user_name} and {user_language} 
    from the session state.
    """
    context_prefix = """
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


def get_consultant_agent() -> SequentialAgent:
    """
    Factory function to create a new instance of the consultant agent and its sub-agents.
    This prevents cross-session state contamination and property modification issues.
    """
    # Validate configuration before creating agents
    validate_stage_config()
    
    sub_agents = []
    for stage in STAGES_CONFIG:
        instruction_path = INSTRUCTIONS_DIR / stage["instruction_file"]
        base_instruction = instruction_path.read_text(encoding="utf-8")

        dynamic_instruction = create_dynamic_instruction(base_instruction)

        agent = LlmAgent(
            name=f"stage_{stage['id']}_agent",
            model=MODEL_NAME,
            instruction=dynamic_instruction,
            description=stage["description"],
            output_key=f"stage_{stage['id']}_output",
            tools=[preload_memory_tool, TOOLS_MAP[stage["tool_name"]]]
        )
        sub_agents.append(agent)

    return SequentialAgent(
        name="ProgramRegistrationOrchestrator",
        description="Orchestrates the program registration and payment flow.",
        sub_agents=sub_agents
    )
