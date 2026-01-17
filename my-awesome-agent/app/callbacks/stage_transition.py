"""
Stage Transition Callback
Creates lightweight context snapshots when stages complete.
Stores extracted facts in session.state, NOT full conversation text.
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse


async def stage_transition_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """
    Creates lightweight context snapshot when a stage completes.
    
    This callback:
    1. Extracts key facts from the stage (NOT full text)
    2. Updates session.state with structured metadata
    3. Marks stage as completed
    4. Tracks progress
    
    Args:
        callback_context: Context with session access
        llm_response: The LLM response (not modified)
        
    Returns:
        None (doesn't modify response)
    """
    agent_name = callback_context.agent_name
    logging.info(f"[Stage Transition] 📸 Processing stage: {agent_name}")
    
    # Initialize session.state structure if needed
    _initialize_state_structure(callback_context)
    
    # Extract key facts based on the stage
    extracted_facts = await _extract_key_facts_for_stage(callback_context, agent_name)
    
    # Update extracted_data in state
    if extracted_facts:
        callback_context.state['extracted_data'].update(extracted_facts)
        logging.info(f"[Stage Transition] ✅ Extracted {len(extracted_facts)} facts for {agent_name}")
    
    # Mark stage as completed
    callback_context.state['stage_completion'][agent_name] = {
        "completed": True,
        "timestamp": datetime.now().isoformat(),
        "event_count": len([e for e in callback_context.session.events if e.author == agent_name])
    }
    
    # Update current stage tracking
    callback_context.state['current_stage_name'] = agent_name
    callback_context.state['turn_count'] = callback_context.state.get('turn_count', 0) + 1
    
    # Log state size for monitoring
    state_size = len(json.dumps(callback_context.state))
    logging.info(f"[Stage Transition] 📊 State size: {state_size} bytes (~{state_size/1024:.1f} KB)")
    logging.info(f"[Stage Transition] 📋 Completed stages: {list(callback_context.state['stage_completion'].keys())}")
    
    return None  # Don't modify the response


def _initialize_state_structure(callback_context: CallbackContext):
    """Initialize session.state with required structure"""
    
    if 'extracted_data' not in callback_context.state:
        callback_context.state['extracted_data'] = {}
    
    if 'stage_completion' not in callback_context.state:
        callback_context.state['stage_completion'] = {}
    
    if 'workflow_status' not in callback_context.state:
        callback_context.state['workflow_status'] = "IN_PROGRESS"
    
    if 'turn_count' not in callback_context.state:
        callback_context.state['turn_count'] = 0


async def _extract_key_facts_for_stage(
    callback_context: CallbackContext,
    agent_name: str
) -> Dict[str, Any]:
    """
    Extract key facts from stage output.
    Returns ONLY structured facts, NOT full conversation text.
    """
    
    # Get the stage output from state (saved via output_key)
    output_key_map = {
        "CompanyContext": "company_context",
        "ProjectOverview": "project_overview",
        "CurrentWorkflow": "current_workflow",
        "ProblemStatement": "problem_statement",
        "SolutionVision": "solution_vision",
        "SuccessCriteria": "success_criteria",
        "GenerationSignoff": "generation_signoff"
    }
    
    output_key = output_key_map.get(agent_name)
    if not output_key:
        logging.warning(f"[Stage Transition] ⚠️  No output_key mapping for agent: {agent_name}")
        return {}
    
    # Get the output from state (NOT from events - output_key automatically saves there)
    stage_output = callback_context.state.get(output_key, "")
    
    if not stage_output:
        logging.warning(f"[Stage Transition] ⚠️  No output found for {agent_name} (key: {output_key})")
        return {}
    
    logging.info(f"[Stage Transition] 📝 Extracting facts from {len(str(stage_output))} chars")
    
    # Extract facts based on stage
    facts = {}
    
    if agent_name == "CompanyContext":
        facts = _extract_company_facts(stage_output, callback_context.state.get('company_research_results', ''))
    
    elif agent_name == "ProjectOverview":
        facts = _extract_project_facts(stage_output)
    
    elif agent_name == "CurrentWorkflow":
        facts = _extract_workflow_facts(stage_output)
    
    elif agent_name == "ProblemStatement":
        facts = _extract_problem_facts(stage_output)
    
    elif agent_name == "SolutionVision":
        facts = _extract_solution_facts(stage_output)
    
    elif agent_name == "SuccessCriteria":
        facts = _extract_criteria_facts(stage_output)
    
    elif agent_name == "GenerationSignoff":
        facts = {"signoff_confirmed": True}
    
    return facts


def _extract_company_facts(company_context: str, research_results: str) -> Dict[str, Any]:
    """Extract structured facts from company context"""
    
    facts = {}
    
    # Simple heuristic extraction (could be enhanced with LLM)
    text = company_context + " " + research_results
    
    # Extract company name
    if "NxtWave" in text or "Nestwave" in text:
        if "NxtWave Disruptive Technologies" in text:
            facts["company_name"] = "NxtWave Disruptive Technologies"
        elif "Nestwave" in text:
            facts["company_name"] = "Nestwave"
    
    # Extract industry hints
    if "IoT" in text or "geolocation" in text:
        facts["industry"] = "IoT / Geolocation"
    elif "education" in text.lower() or "tech careers" in text.lower():
        facts["industry"] = "EdTech / Career Development"
    
    # Extract target audience hints
    if "students" in text.lower() and "professionals" in text.lower():
        facts["target_audience"] = "Students and professionals seeking tech careers"
    elif "IoT applications" in text:
        facts["target_audience"] = "IoT device manufacturers"
    
    logging.info(f"[Stage Transition] 🏢 Extracted company facts: {list(facts.keys())}")
    return facts


def _extract_project_facts(project_overview: str) -> Dict[str, Any]:
    """Extract structured facts from project overview"""
    
    facts = {}
    
    # Extract project name from first line or title
    lines = project_overview.split('\n')
    if lines:
        # Simple heuristic: first substantial line is likely project name
        for line in lines:
            if len(line.strip()) > 10 and len(line.strip()) < 100:
                facts["project_name"] = line.strip().replace('#', '').replace('**', '')
                break
    
    # Extract project type hints
    text_lower = project_overview.lower()
    if "platform" in text_lower:
        facts["project_type"] = "Platform"
    elif "application" in text_lower or "app" in text_lower:
        facts["project_type"] = "Application"
    elif "system" in text_lower:
        facts["project_type"] = "System"
    
    logging.info(f"[Stage Transition] 🎯 Extracted project facts: {list(facts.keys())}")
    return facts


def _extract_workflow_facts(workflow_desc: str) -> Dict[str, Any]:
    """Extract structured facts from workflow description"""
    
    facts = {}
    
    # Count steps/pain points mentioned
    text_lower = workflow_desc.lower()
    pain_point_keywords = ["problem", "issue", "difficult", "slow", "manual", "time-consuming", "inefficient"]
    
    pain_points_count = sum(1 for keyword in pain_point_keywords if keyword in text_lower)
    
    if pain_points_count > 0:
        facts["pain_points_identified"] = pain_points_count
        facts["has_pain_points"] = True
    
    logging.info(f"[Stage Transition] 🔄 Extracted workflow facts: {list(facts.keys())}")
    return facts


def _extract_problem_facts(problem_statement: str) -> Dict[str, Any]:
    """Extract structured facts from problem statement"""
    
    facts = {}
    
    # Extract problem summary (first sentence or first 100 chars)
    sentences = problem_statement.split('.')
    if sentences:
        facts["problem_summary"] = sentences[0].strip()[:150]
    
    logging.info(f"[Stage Transition] ⚠️  Extracted problem facts: {list(facts.keys())}")
    return facts


def _extract_solution_facts(solution_vision: str) -> Dict[str, Any]:
    """Extract structured facts from solution vision"""
    
    facts = {}
    
    # Extract solution summary
    sentences = solution_vision.split('.')
    if sentences:
        facts["solution_summary"] = sentences[0].strip()[:150]
    
    # Check if AI/ML mentioned
    text_lower = solution_vision.lower()
    if "ai" in text_lower or "machine learning" in text_lower or "ml" in text_lower:
        facts["uses_ai"] = True
    
    logging.info(f"[Stage Transition] 💡 Extracted solution facts: {list(facts.keys())}")
    return facts


def _extract_criteria_facts(success_criteria: str) -> Dict[str, Any]:
    """Extract structured facts from success criteria"""
    
    facts = {}
    
    # Count KPIs mentioned
    text_lower = success_criteria.lower()
    kpi_keywords = ["metric", "kpi", "measure", "%", "percentage", "time", "cost", "revenue"]
    
    kpis_mentioned = sum(1 for keyword in kpi_keywords if keyword in text_lower)
    
    if kpis_mentioned > 0:
        facts["kpis_defined"] = True
        facts["kpi_count_estimate"] = kpis_mentioned
    
    logging.info(f"[Stage Transition] 📊 Extracted criteria facts: {list(facts.keys())}")
    return facts

