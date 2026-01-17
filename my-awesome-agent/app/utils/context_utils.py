"""
Context Utilities for Event-Based Context Extraction
Extracts conversation context from session.events instead of session.state
"""

import logging
from typing import List, Dict, Any, Optional
from google.adk.sessions import Session


def get_stage_context(session: Session, stage_name: str, turns: int = 5) -> Dict[str, Any]:
    """
    Extract context for a specific stage from session.events
    
    Args:
        session: ADK Session object with events
        stage_name: Agent name (e.g., "CompanyContext", "ProjectOverview")
        turns: Number of recent turns to include
        
    Returns:
        Dictionary with stage_output, user_questions, and tool_results
    """
    logging.info(f"[Context Utils] 🔍 Extracting context for stage: {stage_name}")
    
    stage_events = []
    user_events = []
    turn_count = 0
    
    # Filter events by author (reverse to get most recent first)
    for event in reversed(session.events):
        if event.author == stage_name:
            stage_events.append(event)
            turn_count += 1
        elif event.author == "user":
            user_events.append(event)
        
        # Stop after collecting enough turns
        if turn_count >= turns:
            break
    
    # Reverse to get chronological order
    stage_events.reverse()
    user_events.reverse()
    
    # Extract text content
    context = {
        "stage_output": [],
        "user_questions": [],
        "tool_results": []
    }
    
    for event in stage_events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    context["stage_output"].append(part.text)
                if hasattr(part, 'function_response') and part.function_response:
                    context["tool_results"].append({
                        "name": part.function_response.name,
                        "response": str(part.function_response.response)
                    })
    
    for event in user_events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    context["user_questions"].append(part.text)
    
    logging.info(f"[Context Utils] ✅ Extracted: {len(context['stage_output'])} outputs, "
                 f"{len(context['user_questions'])} questions, {len(context['tool_results'])} tool results")
    
    return context


def get_all_stage_contexts(session: Session, stage_names: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Extract context for all specified stages
    
    Args:
        session: ADK Session object
        stage_names: List of agent names to extract
        
    Returns:
        Dictionary mapping stage_name to its context
    """
    logging.info(f"[Context Utils] 📊 Extracting context for {len(stage_names)} stages")
    
    all_contexts = {}
    for stage_name in stage_names:
        all_contexts[stage_name] = get_stage_context(session, stage_name)
    
    return all_contexts


def get_recent_conversation(session: Session, num_turns: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent conversation turns from session.events
    
    Args:
        session: ADK Session object
        num_turns: Number of recent turns to retrieve
        
    Returns:
        List of conversation turns with author and content
    """
    logging.info(f"[Context Utils] 💬 Extracting last {num_turns} conversation turns")
    
    conversation = []
    recent_events = list(reversed(session.events))[:num_turns * 2]  # Approximate
    
    for event in reversed(recent_events):  # Back to chronological order
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    conversation.append({
                        "author": event.author,
                        "text": part.text,
                        "timestamp": getattr(event, 'timestamp', None)
                    })
    
    logging.info(f"[Context Utils] ✅ Extracted {len(conversation)} conversation turns")
    return conversation


def get_transcription_context(session: Session, author_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract transcribed conversation from session.events
    (Only available if audio transcription is enabled in RunConfig)
    
    Args:
        session: ADK Session object
        author_filter: Optional filter by author (e.g., "user" or agent name)
        
    Returns:
        List of transcriptions with author and text
    """
    logging.info(f"[Context Utils] 🎤 Extracting transcriptions (filter: {author_filter or 'all'})")
    
    transcriptions = []
    
    for event in session.events:
        # User speech transcription
        if hasattr(event, 'input_transcription') and event.input_transcription:
            if not author_filter or author_filter == "user":
                transcriptions.append({
                    "author": "user",
                    "text": event.input_transcription,
                    "timestamp": getattr(event, 'timestamp', None),
                    "type": "input"
                })
        
        # Model speech transcription
        if hasattr(event, 'output_transcription') and event.output_transcription:
            if not author_filter or author_filter == event.author:
                transcriptions.append({
                    "author": event.author,
                    "text": event.output_transcription,
                    "timestamp": getattr(event, 'timestamp', None),
                    "type": "output"
                })
    
    logging.info(f"[Context Utils] ✅ Extracted {len(transcriptions)} transcriptions")
    return transcriptions


def extract_stage_output_by_key(session: Session, output_key: str) -> Optional[str]:
    """
    Extract the output from a specific stage by its output_key
    This gets the text that was saved via the agent's output_key
    
    Args:
        session: ADK Session object
        output_key: The output_key of the agent (e.g., "company_context")
        
    Returns:
        The extracted text output or None
    """
    logging.info(f"[Context Utils] 🔑 Extracting output for key: {output_key}")
    
    # The output_key data is stored in session state, but we want to get it from events
    # to have the full conversation context
    
    # First, try to get from state (quick lookup)
    if hasattr(session, 'state') and output_key in session.state:
        output = session.state.get(output_key)
        if output:
            logging.info(f"[Context Utils] ✅ Found in state: {len(str(output))} chars")
            return str(output)
    
    # If not in state or we want more context, extract from events
    # Find the agent name that uses this output_key
    # This is less reliable but provides full event context
    for event in reversed(session.events):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text and len(part.text) > 50:  # Skip very short texts
                    # This is a heuristic - in practice you'd want to track agent->output_key mapping
                    logging.info(f"[Context Utils] ℹ️  Found text from {event.author}")
                    return part.text
    
    logging.warning(f"[Context Utils] ⚠️  No output found for key: {output_key}")
    return None


def format_context_for_prompt(contexts: Dict[str, Dict[str, Any]], include_tools: bool = True) -> str:
    """
    Format extracted contexts into a readable string for LLM prompts
    
    Args:
        contexts: Dictionary of stage contexts from get_all_stage_contexts()
        include_tools: Whether to include tool results
        
    Returns:
        Formatted string ready for LLM prompts
    """
    formatted = []
    
    for stage_name, context in contexts.items():
        formatted.append(f"\n### {stage_name}")
        formatted.append("\n**Agent Output:**")
        formatted.append("\n".join(context["stage_output"]) or "No output")
        
        if context["user_questions"]:
            formatted.append("\n**User Questions:**")
            formatted.append("\n".join(context["user_questions"]))
        
        if include_tools and context["tool_results"]:
            formatted.append("\n**Tool Results:**")
            for tool_result in context["tool_results"]:
                formatted.append(f"- {tool_result['name']}: {tool_result['response'][:200]}...")
        
        formatted.append("\n" + "-" * 80)
    
    return "\n".join(formatted)


def get_conversation_summary(session: Session) -> Dict[str, Any]:
    """
    Get high-level summary statistics from session.events
    
    Returns:
        Dictionary with conversation statistics
    """
    total_events = len(session.events)
    
    # Count by author
    author_counts = {}
    user_turns = 0
    agent_turns = 0
    
    for event in session.events:
        author = event.author
        if author:
            author_counts[author] = author_counts.get(author, 0) + 1
            if author == "user":
                user_turns += 1
            else:
                agent_turns += 1
    
    summary = {
        "total_events": total_events,
        "user_turns": user_turns,
        "agent_turns": agent_turns,
        "authors": list(author_counts.keys()),
        "author_distribution": author_counts
    }
    
    logging.info(f"[Context Utils] 📈 Conversation summary: {total_events} events, "
                 f"{user_turns} user turns, {agent_turns} agent turns")
    
    return summary

