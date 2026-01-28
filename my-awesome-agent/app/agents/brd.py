from pathlib import Path
from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

# Helper to load instructions
def load_instruction(filename):
    path = Path(__file__).parent.parent / "instructions" / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

MODEL_NAME_FLASH = "gemini-live-2.5-flash-preview-native-audio-09-2025"
MODEL_NAME_PRO = "gemini-2.5-pro"

# 1. BRD Manager (Conversational Interface)
brd_manager = LlmAgent(
    name="BRD_Manager",
    model=MODEL_NAME_FLASH,
    instruction=load_instruction("brd_manager.md"),
    description="Manages the BRD generation process and collects user feedback.",
    tools=[PreloadMemoryTool()]
)

# 2. BRD Drafter (Backend Generator)
brd_drafter = LlmAgent(
    name="BRD_Drafter",
    model=MODEL_NAME_PRO,
    instruction=load_instruction("brd_drafter.md"),
    description="Specialist that generates the BRD markdown.",
    output_key="final_brd", # Backend will listen for this key
    tools=[PreloadMemoryTool()]
)

# 3. Refinement Loop
refinement_loop = LoopAgent(
    name="BRD_Refinement_Loop",
    description="Continuous loop for BRD refinement: Manager <-> Drafter.",
    sub_agents=[brd_manager, brd_drafter],
    max_iterations=50 # High limit to allow extended refinement as requested
)
