"""Dedicated search agent for company research."""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search


# Create a dedicated search agent for company research
search_agent = LlmAgent(
    name="CompanyResearcher",
    model="gemini-2.0-flash",
    instruction="""You are a research assistant specialized in finding company information.

When given a company name, you MUST:
1. Use the google_search tool to find the company's official website and mission
2. Search for their main products and services
3. Search for their target audience or customer base
4. Synthesize the results into a concise profile

Extract and provide:
- Full Company Name
- Mission Summary (1-2 sentences)
- Key Products/Services (2-3 main ones)
- Target Audience (who they serve)

Be thorough but concise. Focus on factual, verifiable information.""",
    tools=[google_search],
    description="Researches company information, products, and target audience.",
    output_key="company_research_results"
)

