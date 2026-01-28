"""Consultant Agent with dynamic stage-based instructions."""

import os
from pathlib import Path
from google.adk.agents import LlmAgent , SequentialAgent
from google.adk.tools import FunctionTool, AgentTool ,google_search
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
# Import the new tool function
from .tools import (
    advance_stage, 
    finalize_discovery, 
    get_current_stage, 
    generate_brd_direct,
    complete_program_explanation,
    complete_payment_structure
)

from .search_agent import search_agent


# Model Name Configuration:
# - For Gemini Live API (GOOGLE_GENAI_USE_VERTEXAI=FALSE):
#   Use: gemini-2.5-flash-native-audio-preview-09-2025
# - For Vertex AI Live API (GOOGLE_GENAI_USE_VERTEXAI=TRUE):
#   Use: gemini-live-2.5-flash-preview-native-audio-09-2025 or
#        gemini-live-2.5-flash-native-audio
#   Available at: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live

# Read model name from environment variable, fallback to default
MODEL_NAME = os.getenv(
    "GEMINI_MODEL_NAME",
    "gemini-2.0-flash-exp"
) 

# Load instruction files
INSTRUCTIONS_DIR = Path(__file__).parent.parent / "instructions"

def load_instruction(filename):
    path = Path(__file__).parent.parent / "instructions" / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# ============================================================================
# SHARED TOOLS
# ============================================================================

advance_stage_tool = FunctionTool(advance_stage)
search_agent_tool = AgentTool(agent=search_agent)
preload_memory_tool = PreloadMemoryTool()
get_stage_tool = FunctionTool(get_current_stage)

# Stage-specific tools
complete_stage_0_tool = FunctionTool(complete_program_explanation)
complete_stage_1_tool = FunctionTool(complete_payment_structure)


# NEW: Create the FunctionTool for direct generation
generate_brd_tool = FunctionTool(
    generate_brd_direct
)

program_explanation_instruction = (
    INSTRUCTIONS_DIR / "program_explanation.md"
).read_text(encoding="utf-8")

# ============================================================================
# SPECIALIST SUB-AGENTS
# ============================================================================

program_explanation_agent = LlmAgent(
    name="program_explanation_agent",
    model=MODEL_NAME,
    instruction=program_explanation_instruction,
    description="Explains the NxtWave CCBP 4.0 program value and learning journey.",
    output_key="program_explanation",
    tools=[preload_memory_tool, complete_stage_0_tool]
)

payment_structure_agent = LlmAgent(
    name="payment_structure_agent",
    model=MODEL_NAME,
    instruction=(INSTRUCTIONS_DIR / "payment_structure.md").read_text(
        encoding="utf-8"
    ),
    description="Presents payment options (Full Payment vs EMI) and routes to next stage.",
    output_key="payment_structure",
    tools=[preload_memory_tool, complete_stage_1_tool]
)






consultant_agent = SequentialAgent(
    name="ProgramRegistrationOrchestrator",
    description="Orchestrates the program registration and payment flow.",
    sub_agents=[
        program_explanation_agent,
        payment_structure_agent
    ]
)
