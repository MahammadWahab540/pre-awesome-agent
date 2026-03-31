"""Tool functions for stage management and workflow control."""
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

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

# --- Consent Tracking Utility ---
def track_confirmation(tool_context: ToolContext, stage_name: str, confirmation_type: str, user_response: str = "explicit_yes") -> None:
    """
    Tracks user confirmations for legal compliance and audit trails.
    
    Args:
        tool_context: The current tool execution context
        stage_name: Name of the stage (e.g., "Program Explanation", "Payment Structure")
        confirmation_type: Type of confirmation (e.g., "stage_complete", "payment_understanding")
        user_response: The user's response (default: "explicit_yes")
    """
    from datetime import datetime
    
    if "confirmations" not in tool_context.state:
        tool_context.state["confirmations"] = []
    
    confirmation_record = {
        "stage": stage_name,
        "type": confirmation_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_response": user_response,
        "session_id": tool_context.session.id if tool_context.session else None
    }
    
    tool_context.state["confirmations"].append(confirmation_record)
    logger.info(f"📝 Tracked confirmation: {stage_name} - {confirmation_type} at {confirmation_record['timestamp']}")

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


def continuous_conversation(tool_context: ToolContext, **_: Any) -> str:
    """Compatibility no-op for hallucinated live-mode tool calls.

    Gemini Live occasionally invents a `continuous_conversation` tool call even
    when that tool is not registered. Registering this safe alias avoids
    crashing the entire session and steers the model back into the stage script.
    """
    logger.warning("⚠️ Compatibility tool invoked: continuous_conversation")

    if tool_context.state.get("is_resuming"):
        return (
            "SYSTEM_NOTE: The session is resuming. Greet the user and continue "
            "naturally from the current stage. Do NOT replay previous stage "
            "completions and do NOT call any completion tool until the user "
            "responds in the current turn."
        )

    return (
        "SYSTEM_NOTE: Continue the current stage conversation using the scripted "
        "flow. Do NOT advance the stage yet, do NOT call any completion tool "
        "yet, and do NOT call continuous_conversation again unless explicitly "
        "instructed by the system."
    )

def advance_stage(tool_context: ToolContext, stage_index: int, reason: str = "Stage completed", next_index: int = None) -> str:
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
        return f"SYSTEM_NOTE: Stage {stage_index} has already been completed. The current active stage is Stage {current_stage}. Do NOT say 'I am ready when you are' — that phrase is strictly forbidden. You must actively continue the conversation by following the turn-by-turn instructions for Stage {current_stage}. Speak to the user directly according to your current stage script."

    next_stage = next_index if next_index is not None else current_stage + 1
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
                _update_task = loop.create_task(manager.send_stage_update(tool_context.session.id, next_stage))
                _update_task.add_done_callback(
                    lambda t: logger.error("Frontend stage update failed: %s", t.exception())
                    if not t.cancelled() and t.exception() else None
                )
    except Exception as e:
        logger.error(f"Failed to trigger frontend update: {e}")
        
    tool_context.state["_should_terminate_agent"] = True
    return f"SYSTEM_NOTE: Stage {stage_index} advanced to {next_stage}. ROUTER ACTION REQUIRED: Immediately Transfer to the Stage {next_stage} agent and force them to introduce themselves. Do not wait for user input."

def complete_program_explanation(tool_context: ToolContext, payment_path: str = "") -> str:
    """Successfully completes Program Explanation stage and captures the selected payment path (emi, full_payment, or credit_card)."""

    # Guard: block stage advancement during session resumption (history replay)
    if tool_context.state.get("is_resuming"):
        logger.warning("🔄 complete_program_explanation blocked: session is resuming, ignoring history replay call.")
        return (
            "SYSTEM_NOTE: This session is being resumed. Do NOT replay previous stage completions. "
            "Greet the user and continue the conversation naturally from the current stage."
        )

    # ✅ IDEMPOTENCY GUARD: Prevent double-call hallucination loop.
    # If the model calls this tool a second time after it already succeeded
    # (e.g., due to a live-mode streaming timing issue), block it silently.
    if tool_context.state.get("stage_1_confirmed", False):
        logger.warning("🚫 complete_program_explanation blocked: already called and confirmed in this session (stage_1_confirmed=True).")
        return (
            "SYSTEM_NOTE: Stage 1 has already been completed and confirmed. "
            "Do NOT ask the user any further questions. "
            "Do NOT repeat Turn 11 or any other turn. "
            "Go completely silent — the system is handling the stage transition. "
            "Say nothing more."
        )

    # Guard: reject invalid or missing payment_path — never silently default to Stage 2 (EMI)
    if payment_path not in ["emi", "full_payment", "credit_card"]:
        logger.error(f"🚫 complete_program_explanation blocked: invalid payment_path='{payment_path}'. Must be 'emi', 'full_payment', or 'credit_card'. Stage NOT advanced.")
        return (
            f"SYSTEM_NOTE: complete_program_explanation was called with an invalid or missing payment_path='{payment_path}'. "
            "Stage has NOT been advanced. You must confirm the user's chosen payment path (emi, full_payment, or credit_card) "
            "and call this tool again with the correct payment_path argument. Do NOT proceed to Stage 2 without a valid payment_path."
        )

    tool_context.state["payment_path"] = payment_path
    # Mark as confirmed to prevent any repeat calls in this session
    tool_context.state["stage_1_confirmed"] = True
    logger.info(f"✅ complete_program_explanation SUCCEEDED: Captured payment path: '{payment_path}'. Set stage_1_confirmed=True to prevent repeat calls.")

    # ROUTING LOGIC:
    # If payment_path is full_payment or credit_card, skip Stage 2 (EMI Onboarding)
    # We set next_index to 2 (beyond our 2 agents) to effectively end the sequence.
    next_index = None
    if payment_path in ["full_payment", "credit_card"]:
        next_index = 2
        logger.info(f"🔀 Non-EMI path detected. Skipping to handoff (next_index={next_index}).")

    result = advance_stage(tool_context, 0, next_index=next_index)
    # Only track confirmation if stage actually advanced (not a blocked/hallucinated call)
    if "advanced to" in result:
        track_confirmation(
            tool_context,
            stage_name="Program Explanation",
            confirmation_type="stage_complete",
            user_response="explicit_yes"
        )
    return result

def complete_payment_structure(tool_context: ToolContext) -> str:
    """Successfully completes Payment Structure stage."""
    result = advance_stage(tool_context, 1)
    # Only track confirmation if stage actually advanced (not a blocked/hallucinated call)
    if "advanced to" in result:
        track_confirmation(
            tool_context,
            stage_name="Payment Structure",
            confirmation_type="stage_complete",
            user_response="explicit_yes"
        )
    return result

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
