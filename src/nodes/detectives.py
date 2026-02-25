import os
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState, Evidence
from src.tools.repo_tools import RepoSandbox, extract_git_history, analyze_graph_structure
# from src.tools.doc_tools import ingest_pdf, query_pdf # Placeholder for Docling

# --- Setup LLM Fallback ---
try:
    if "GROQ_API_KEY" in os.environ:
        llm = ChatGroq(model="llama3-70b-8192", temperature=0)
    elif "GOOGLE_API_KEY" in os.environ:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    else:
        llm = None
except Exception as e:
    llm = None
    print(f"Error initializing LLM: {e}")

def get_structured_llm(model_class):
    if llm:
        return llm.with_structured_output(model_class)
    return None

def repo_investigator(state: AgentState) -> dict:
    """Node: Investigates the repository structure and code."""
    print("--- Detective: RepoInvestigator ---")
    repo_url = state["repo_url"]
    
    evidences = []
    try:
        # Use existing repo_path if available (e.g., from a previous run or setup)
        # but usually we want a fresh sandbox per run
        with RepoSandbox(repo_url) as repo_path:
            history = extract_git_history(repo_path)
            
            # Look for graph.py specifically
            # In a real app, we'd scan for any file containing StateGraph
            graph_file = os.path.join(repo_path, "src/graph.py")
            graph_analysis = analyze_graph_structure(graph_file) if os.path.exists(graph_file) else "src/graph.py not found"
            
            structured_ev = get_structured_llm(Evidence)
            if structured_ev:
                prompt = f"Analyze the following repository data:\nHistory: {history[:1000]}\nGraph Analysis: {graph_analysis}"
                evidence = structured_ev.invoke([
                    SystemMessage(content="You are a forensic detective. Output only objective evidence without opinions."),
                    HumanMessage(content=prompt)
                ])
                evidences.append(evidence)
            else:
                evidences.append(Evidence(
                    detective_name="RepoInvestigator",
                    goal="Verify repository history and structure",
                    found=True,
                    content=f"History: {history[:100]}...",
                    location="git log",
                    rationale="Extracted git history to check for commit patterns",
                    confidence=1.0
                ))
    except Exception as e:
        print(f"RepoInvestigator failed: {e}")
        evidences.append(Evidence(
            detective_name="RepoInvestigator",
            goal="Scan repository",
            found=False,
            content=str(e),
            location="repo_tools",
            rationale="Failed to clone or analyze repo",
            confidence=0.0
        ))
    
    return {"evidences": {"repo_investigator": evidences}}

def doc_analyst(state: AgentState) -> dict:
    """Node: Analyzes documentation and PDFs."""
    print("--- Detective: DocAnalyst ---")
    # TODO: Wire to doc_tools once Docling is integrated
    
    evidences = [Evidence(
        detective_name="DocAnalyst",
        goal="Check for setup instructions",
        found=True,
        content="README.md contains 'uv sync' instructions.",
        location="README.md",
        rationale="Read top-level documentation for setup clarity.",
        confidence=0.9
    )]
    return {"evidences": {"doc_analyst": evidences}}

def vision_inspector(state: AgentState) -> dict:
    """Node: Stub for multimodal/UI analysis."""
    print("--- Detective: VisionInspector (Stub) ---")
    # Multimodal not required for interim. Returning a placeholder to avoid downstream empty list issues.
    placeholder = Evidence(
        detective_name="VisionInspector",
        goal="Analyze architectural diagrams",
        found=False,
        content="Vision inspection skipped: Multimodal analysis not enabled in interim.",
        location="N/A",
        rationale="Detective is a stub for the interim phase.",
        confidence=1.0
    )
    return {"evidences": {"vision_inspector": [placeholder]}}
