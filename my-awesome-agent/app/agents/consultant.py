import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

# Ensure environment variables are loaded
load_dotenv(Path(__file__).parent.parent / ".env")

from .patched_sequential_agent import PatchedSequentialAgent

# Import tool functions for stage completion
from .tools import (
    complete_program_explanation,
    complete_payment_structure
)
from ..callbacks.stage_management import stage_management_callback

# Read model name from environment variable.
# Live API requires a gemini-live-* model; auto-fallback if a non-live model is configured.
DEFAULT_LIVE_MODEL = "gemini-live-2.5-flash-native-audio"
_configured_model_raw = os.getenv("GEMINI_MODEL_NAME")
_configured_model = (
    _configured_model_raw.strip()
    if isinstance(_configured_model_raw, str) and _configured_model_raw.strip()
    else None
)
if _configured_model and not _configured_model.startswith("gemini-live-"):
    MODEL_NAME = DEFAULT_LIVE_MODEL
else:
    MODEL_NAME = _configured_model or DEFAULT_LIVE_MODEL

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
logger = logging.getLogger(__name__)

if _configured_model and MODEL_NAME != _configured_model:
    logger.warning(
        "Configured GEMINI_MODEL_NAME=%r is not Live API compatible. "
        "Using fallback model %r.",
        _configured_model,
        MODEL_NAME,
    )


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
        error_message = "\nStage configuration validation failed:\n" + "\n".join(
            f"  - {err}" for err in errors
        )
        raise ValueError(error_message)

    logger.info("Stage configuration validated successfully")


def create_dynamic_instruction(base_instruction: str):
    """
    Creates a string template with placeholders for user context.
    ADK's LlmAgent automatically resolves {user_name}, {user_language},
    and {current_stage_index} from the session state.
    """
    context_prefix = """
# USER CONTEXT (CRITICAL - MUST FOLLOW)
- **User Name:** {user_name}
- **Preferred Language:** {user_language}
- **Current Stage Index:** {current_stage_index}
- **Payment Path Chosen (from Stage 1):** {payment_path}

# HARD STATE GUARD (HIGHEST PRIORITY)
You are currently in Stage {current_stage_index} of the NxtWave Program Registration flow.

If {current_stage_index} > 0, you are STRICTLY FORBIDDEN from repeating any initial greeting from a prior stage or saying "I am ready when you are".

You MUST immediately proceed to the logic defined for the CURRENT STAGE in your instructions below.

# SESSION CONTEXT
- If `payment_path` is "full_payment" or "credit_card": the user already selected a non-EMI path in Stage 1. Handle accordingly per your stage instructions.
- If `payment_path` is "emi": the user selected the No-Cost EMI path and should proceed through the full EMI onboarding flow.
- If `payment_path` is not yet set (empty or missing): you are in Stage 1 — proceed with qualification as instructed.

# GROUNDING INSTRUCTIONS (NO HALLUCINATIONS — MANDATORY)
1. You are an AI Program Registration Expert (PRE) for NxtWave.
2. Do NOT make up facts, loan rates, NBFC names (unless user asks), pricing, or policies not stated in your instructions.
3. Do NOT promise loan approval — eligibility is determined by the NBFC, not NxtWave.
4. If you do not know the answer, say: "Let me connect you with a senior counselor who can answer that precisely."
5. **STRICTLY FORBIDDEN PHRASE — NEVER SAY THIS UNDER ANY CIRCUMSTANCES:** "I am ready when you are." — This phrase is absolutely prohibited in every stage, every turn, and every scenario. If you receive a SYSTEM_NOTE, you must still speak to the user actively according to your current stage script.
6. Do NOT speak any content outside of what is defined in your stage instructions. Every sentence you say must map to a specific turn in your stage script. If you are unsure what to say, re-read your stage instructions and deliver the next checkpoint question.
7. When you receive a SYSTEM_NOTE from a tool, do NOT read it aloud or repeat it to the user. It is an internal system directive only. Continue speaking to the user according to your stage script.
8. **NEVER CALL A COMPLETION TOOL PREMATURELY:** You must complete all conversation turns sequentially. You are strictly forbidden from calling a stage completion tool immediately upon connecting.

# LANGUAGE RULES (MANDATORY)
1. **Always** address the user by their name: "{user_name}".
2. **Always** speak in {user_language}.
   - If {user_language} is Telugu, Tamil, Hindi, or any Indic language: speak 70% regional + 30% English.
   - If user prefers, adapt toward 90% regional.
   - Technical terms — EMI, KYC, NBFC, RBI, co-applicant, portal, PAN, Aadhaar — always remain in English.
3. Even if the instructions below are in English, your SPOKEN OUTPUT must be in {user_language}.
4. The user's name is "{user_name}" — use only this name. Do NOT invent names.

---
"""
    return context_prefix + base_instruction



def get_consultant_agent() -> PatchedSequentialAgent:
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

        from google.genai import types
        agent = LlmAgent(
            name=f"stage_{stage['id']}_agent",
            model=MODEL_NAME,
            instruction=dynamic_instruction,
            output_key=f"stage_{stage['id']}_output",
            generate_content_config=types.GenerateContentConfig(temperature=0.1),
            tools=[preload_memory_tool, TOOLS_MAP[stage["tool_name"]]],
            after_model_callback=stage_management_callback,
        )
        sub_agents.append(agent)

    return PatchedSequentialAgent(
        name="ProgramRegistrationOrchestrator",
        sub_agents=sub_agents
    )
