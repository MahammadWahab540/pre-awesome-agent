# Copyright 2025 Google LLC
# ... (License Header) ...

"""
Multimodal Live Agent with DatabaseSessionService and VertexAiMemoryBankService
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import vertexai
from types import SimpleNamespace

# ==============================================================================
# ENVIRONMENT SETUP
# ==============================================================================
load_dotenv()

# ==============================================================================
# FORCE VERTEX AI LOCATION TO US-CENTRAL1
# ==============================================================================
# This overrides Cloud Run's auto-detection of 'asia-south1'
# The gemini-live-*-native-audio models are only available in us-central1
vertexai.init(
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")  # Force US region regardless of where Cloud Run is deployed
)

# ==============================================================================
# ADK IMPORTS & PATCHING
# ==============================================================================
from google.adk.agents import LlmAgent,Agent
from google.adk.apps.app import App, EventsCompactionConfig, ResumabilityConfig
from google.adk.memory import VertexAiMemoryBankService, InMemoryMemoryService
from google.adk.plugins.logging_plugin import LoggingPlugin
import google.adk.flows.llm_flows.contents as contents_module
import google.adk.agents.llm_agent as llm_agent_module

# ==============================================================================
# AGENT IMPORT (Updated)
# ==============================================================================
# UPDATED: Import the consultant_agent directly
from .agents.consultant import consultant_agent 

# ==============================================================================
# APP INITIALIZATION
# ==============================================================================
# app = App(
#     name="app",
#     root_agent=consultant_agent,

#     events_compaction_config=EventsCompactionConfig(
#         compaction_interval=10,
#         overlap_size=2,
#     ),
#     resumability_config=ResumabilityConfig(
#         is_resumable=True
#     )
#     # plugins=[LoggingPlugin()]  # Enable built-in observability
# )


# root_agent = Agent(
#     name="root_agent",
#     model="gemini-live-2.5-flash-preview-native-audio-09-2025",
#     instruction="You are a helpful AI assistant designed to provide accurate and useful information.",
#     tools=[get_weather],
# )

app = App(root_agent=consultant_agent, name="app")