import os
from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState, Evidence

# --- Setup LLM Fallback ---
# Prefer Groq, fallback to Google Generative AI
try:
    if "GROQ_API_KEY" in os.environ:
        llm = ChatGroq(model="llama3-70b-8192", temperature=0)
    elif "GOOGLE_API_KEY" in os.environ:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    else:
        # Stub for local testing if no keys are set
        llm = None
        print("Warning: No LLM API keys found. Nodes will fail if executed without a mock.")
except Exception as e:
    llm = None
    print(f"Error initializing LLM: {e}")

# IMPORTANT: Bind to Pydantic model for structured output
if llm:
    try:
        structured_llm = llm.with_structured_output(Evidence)
    except Exception as e:
        structured_llm = None
        print(f"Error binding structured output: {e}")
else:
    structured_llm = None

def repo_investigator(state: AgentState) -> dict:
    """Node: Investigates the repository structure and code."""
    print("--- Detective: RepoInvestigator ---")
    
    # TODO: Use RepoSandbox tool here to clone and analyze the actual repo
    
    if structured_llm:
        # Stub call to LLM
        prompt = "Analyze the repository for proper dependency management. Output an objective evidence finding."
        evidence = structured_llm.invoke([
            SystemMessage(content="You are a forensic detective. Output only objective evidence without opinions or judgments."),
            HumanMessage(content=prompt)
        ])
    else:
        # Fallback stub evidence
        evidence = Evidence(
            detective_name="RepoInvestigator",
            finding="Found pyproject.toml with uv configuration.",
            source="/pyproject.toml:L1-20",
            confidence=0.95
        )
    
    # Return delta to update the 'evidences' dict in AgentState
    return {"evidences": {"repo_investigator": [evidence]}}

def doc_analyst(state: AgentState) -> dict:
    """Node: Analyzes documentation and PDFs."""
    print("--- Detective: DocAnalyst ---")
    
    # TODO: Use DocTools here to read README.md or standard.pdf
    
    if structured_llm:
        prompt = "Analyze the provided documentation for clear setup instructions. Output an objective evidence finding."
        evidence = structured_llm.invoke([
            SystemMessage(content="You are a forensic detective. Output only objective evidence without opinions or judgments."),
            HumanMessage(content=prompt)
        ])
    else:
        # Fallback stub evidence
        evidence = Evidence(
            detective_name="DocAnalyst",
            finding="Setup instructions are clear and specify uv sync.",
            source="/README.md:Setup Section",
            confidence=0.9
        )
    
    return {"evidences": {"doc_analyst": [evidence]}}
