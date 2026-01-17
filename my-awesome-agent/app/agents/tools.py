"""Tool functions for stage management and workflow control."""
import os
import logging
from pathlib import Path
from typing import Dict, Any

# --- CHANGED: Import the new Google Gen AI SDK (Same as Visualization Service) ---
from google.genai import Client, types
from google.adk.tools import ToolContext

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Helper: Get Vertex AI Client (Same as Visualization Service) ---
def _get_client() -> Client:
    """Get the Gemini client for Vertex AI."""
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-south1")
    
    if not project:
        # Fallback or error if env var is missing
        logger.warning("GOOGLE_CLOUD_PROJECT not set. Attempting default auth.")
    
    return Client(
        vertexai=True,
        project=project,
        location=location
    )

# --- Existing Stage Management Tools ---

def get_current_stage(tool_context: ToolContext) -> str:
    idx = tool_context.state.get("current_stage_index", 0)
    if "current_stage_index" not in tool_context.state:
        tool_context.state["current_stage_index"] = 0
    return str(idx)



def finalize_discovery(tool_context: ToolContext) -> str:
    tool_context.state['workflow_status'] = 'COMPLETED'
    tool_context.state['discovery_completed'] = True
    tool_context.state['current_stage_index'] = 6
    return "✅ Discovery complete! Triggering BRD generation..."

def search_company_info(company_name: str, website: str = None) -> str:
    return f"Researching {company_name}..."

def advance_stage(tool_context: ToolContext, stage_index: int, reason: str = "Stage completed") -> str:
    """
    Increments the current stage index and triggers a frontend update.
    Returns a system note to guide the orchestrator.
    """
    raw_stage = tool_context.state.get("current_stage_index", 0)
    current_stage = int(raw_stage)
    
    # NEW: Guard against history-replay during resumption
    if tool_context.state.get("is_resuming"):
        logger.info(f"🚫 Blocking advance_stage call during resumption (Stage {stage_index})")
        return "SYSTEM_NOTE: Resumption in progress. Please ignore any previous completion signals from history. Introduce yourself to the user and wait for their input before completing this stage."

    # Security Check: Prevent hallucination loops

    if current_stage != stage_index:
        logger.warning(f"⚠️ Hallucination detected: Agent for Stage {stage_index} tried to advance, but system is at Stage {current_stage}")
        return f"SYSTEM_NOTE: You are attempting to complete Stage {stage_index}, but the project is already at Stage {current_stage}. Please wait for the user instructions or just say 'I am ready when you are'."

    next_stage = current_stage + 1
    tool_context.state["current_stage_index"] = next_stage
    
    # --- DIRECT FRONTEND TRIGGER ---
    try:
        if tool_context.session and tool_context.session.id:
            from ..connection_manager import manager
            import asyncio
            
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            
            if loop:
                logger.info(f"🚀 Triggering Frontend Update for Stage {next_stage} (Session: {tool_context.session.id})")
                loop.create_task(manager.send_stage_update(tool_context.session.id, next_stage))
    except Exception as e:
        logger.error(f"Failed to trigger frontend update: {e}")
        
    return f"SYSTEM_NOTE: Stage {stage_index} advanced to {next_stage}. ROUTER ACTION REQUIRED: Immediately Transfer to the Stage {next_stage} agent and force them to introduce themselves. Do not wait for user input."

def complete_program_explanation(tool_context: ToolContext) -> str:
    """Successfully completes Program Explanation stage."""
    return advance_stage(tool_context, 0)

def complete_payment_structure(tool_context: ToolContext) -> str:
    """Successfully completes Payment Structure stage."""
    return advance_stage(tool_context, 1)

def complete_current_workflow(tool_context: ToolContext) -> str:
    """Successfully captures Current Workflow and Pain Points."""
    return advance_stage(tool_context, 2)

def complete_problem_statement(tool_context: ToolContext) -> str:
    """Successfully captures Problem Statement and Impact."""
    return advance_stage(tool_context, 3)

def complete_solution_vision(tool_context: ToolContext) -> str:
    """Successfully captures Solution Vision and MVP features."""
    return advance_stage(tool_context, 4)

def complete_success_criteria(tool_context: ToolContext) -> str:
    """Successfully captures Success Criteria and Metrics."""
    return advance_stage(tool_context, 5)



def generate_brd_direct(tool_context: ToolContext) -> str:
    """
    Directly calls the Gemini Pro model via Vertex AI to generate the BRD 
    and saves it to the session state under 'final_brd'.
    """
    logger.info("🔧 TOOL CALL: Initiating Direct BRD Generation (Vertex AI)...")

    try:
        # 1. Gather Context from Session
        session_data = tool_context.state
        
        # 1.5 Gather Transcripts from Session Events
        transcripts = []
        if hasattr(tool_context.session, 'events'):
            logger.info(f"📜 Processing {len(tool_context.session.events)} events for transcripts...")
            for event in tool_context.session.events:
                # Extract user input transcription
                if hasattr(event, 'input_transcription') and event.input_transcription and event.input_transcription.text:
                    transcripts.append(f"User: {event.input_transcription.text}")
                
                # Extract agent output transcription
                if hasattr(event, 'output_transcription') and event.output_transcription and event.output_transcription.text:
                    transcripts.append(f"Agent: {event.output_transcription.text}")
        
        formatted_transcript = "\n".join(transcripts)
        logger.info(f"📝 Extracted {len(transcripts)} transcript lines.")

        # 2. Load the Drafter Instructions
        try:
            instructions_path = Path(__file__).parent.parent / "instructions" / "brd_drafter.md"
            system_instruction = instructions_path.read_text()
        except Exception as e:
            logger.warning(f"Could not load brd_drafter.md: {e}. Using default prompt.")
            system_instruction = "You are an expert Business Analyst. Generate a professional BRD based on the provided context."

        # 3. Construct the Prompt
        prompt = f"""
        {system_instruction}

        Here is the collected Discovery Data from the session:
        {str(session_data)}

        Here is the full Conversation Transcript:
        {formatted_transcript}

        Please generate the final BRD in Markdown format.
        """

        # 4. Initialize Client (Vertex AI)
        client = _get_client()

        logger.info("🤖 SENDING REQUEST TO VERTEX AI MODEL...")
        
        # We use the Synchronous call here (client.models.generate_content) 
        # because Tool calls in this agent framework are typically blocking.
        response = client.models.generate_content(
            model="gemini-2.5-pro", # Using a stable Vertex model version
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.5 # Balanced for professional documents
            )
        )
        
        generated_content = response.text

        # 5. Store in Session
        tool_context.state['final_brd'] = generated_content

        logger.info("✅ BRD GENERATED AND STORED IN SESSION.")
        
        return "SUCCESS: The BRD has been generated and saved to the session/database. You may now ask the user to review the 'BRD Generation' tab."

    except Exception as e:
        logger.error(f"❌ ERROR generating BRD: {str(e)}")
        return f"Error generating BRD: {str(e)}"