import os
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from src.state import AgentState, Evidence
from src.tools.repo_tools import (
    RepoSandbox,
    extract_git_history,
    analyze_graph_structure,
    analyze_security_features,
    analyze_git_progression,
    get_all_repo_files,
    analyze_state_management,
    analyze_structured_output,
    analyze_judicial_nuance,
    analyze_chief_justice_synthesis
)
from src.tools.doc_tools import extract_images_from_pdf

# --- Setup LLM Fallback ---
def get_detective_llms():
    """Returns LLMs for Detective layer. Primary: Gemini, Fallback: Groq."""
    llms = []
    
    # Primary for Detectives: Gemini
    if os.environ.get("GOOGLE_API_KEY"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llms.append(ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0))
        except ImportError:
            pass
            
    # Fallback 1: Groq
    if os.environ.get("GROQ_API_KEY"):
        llms.append(ChatGroq(model="llama-3.3-70b-versatile", temperature=0))
    
    # Fallback 2: OpenRouter
    if os.environ.get("OPENROUTER_KEY"):
        llms.append(ChatOpenAI(
            model="openrouter/auto-free",
            openai_api_key=os.environ["OPENROUTER_KEY"],
            openai_api_base="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/Natnael-Alemseged/Github-Evaluator",
                "X-Title": "Automaton Auditor"
            },
            temperature=0
        ))
    
    # Local fallback
    llms.append(ChatOpenAI(
        model="llama3.1", 
        openai_api_key="ollama", 
        openai_api_base="http://localhost:11434/v1",
        temperature=0
    ))
    return llms

def repo_cloner(state: AgentState) -> dict:
    """Node: Clones the repository once and stores path in state."""
    print("--- Loader: RepoCloner ---")
    repo_url = state["repo_url"]
    try:
        # We manually manage the sandbox lifecycle
        sandbox = RepoSandbox(repo_url)
        repo_path = sandbox.__enter__()
        all_files = get_all_repo_files(repo_path)
        return {
            "repo_path": repo_path,
            "repo_manifest": all_files
        }
    except Exception as e:
        print(f"RepoCloner failed: {e}")
        return {"repo_path": None, "repo_manifest": []}

def repo_investigator(state: AgentState) -> dict:
    """Node: Investigates the repository structure and code."""
    print("--- Detective: RepoInvestigator ---")
    repo_path = state.get("repo_path")
    if not repo_path:
        return {"evidences": {"repo_investigator": [Evidence(
            detective_name="RepoInvestigator",
            goal="Analyze repo", found=False, content="No repo_path in state", location="None", rationale="Cloning failed", confidence=0.0
        )]}}
    
    evidences = []
    try:
        print(f"--- RepoInvestigator Analyzing: {repo_path} ---")
        
        # 1) Analysis of Graph Structure
        graph_analysis = analyze_graph_structure(repo_path)
        evidences.append(Evidence(
            detective_name="RepoInvestigator",
            goal="Verify fan-out/fan-in and StateGraph structure",
            found="StateGraph" in graph_analysis,
            content=graph_analysis,
            location="src/graph.py",
            rationale="AST analysis of graph definition file.",
            confidence=1.0
        ))
        
        # 2) History Forensics
        history_analysis = extract_git_history(repo_path)
        evidences.append(Evidence(
            detective_name="RepoInvestigator",
            goal="Retrieve git history for effort and atomic commits",
            found=len(history_analysis) > 50,
            content=history_analysis,
            location="Git Log",
            rationale="Used to gauge developer effort and commit quality.",
            confidence=1.0
        ))
        
        # 3) Git Progression
        timeline_analysis = analyze_git_progression(history_analysis)
        evidences.append(Evidence(
            detective_name="RepoInvestigator",
            goal="Verify logical setup -> tools -> graph progression",
            found="Timeline reconstruction:" in timeline_analysis,
            content=timeline_analysis,
            location="Git History Analytics",
            rationale="Analyzes temporal development stages.",
            confidence=1.0
        ))

        # 4) State Management
        state_analysis = analyze_state_management(repo_path)
        evidences.append(Evidence(
            detective_name="RepoInvestigator",
            goal="Verify Pydantic models and Annotated reducers in state",
            found="Pydantic BaseModel found" in state_analysis,
            content=state_analysis,
            location="src/state.py",
            rationale="Keyword scan for State Management Rigor.",
            confidence=1.0
        ))

        # 5) Structured Output
        output_analysis = analyze_structured_output(repo_path)
        evidences.append(Evidence(
            detective_name="RepoInvestigator",
            goal="Verify .with_structured_output() in judges",
            found="Uses '.with_structured_output()'" in output_analysis,
            content=output_analysis,
            location="src/nodes/judges.py",
            rationale="Keyword scan for Structured Output enforcement.",
            confidence=1.0
        ))

        # 6) Judicial Nuance
        nuance_analysis = analyze_judicial_nuance(repo_path)
        evidences.append(Evidence(
            detective_name="RepoInvestigator",
            goal="Verify distinct persona instructions",
            found="Three distinct personas defined" in nuance_analysis,
            content=nuance_analysis,
            location="src/nodes/judges.py",
            rationale="Keyword scan for persona-specific system prompt instructions.",
            confidence=1.0
        ))
        
        # 7) Chief Justice Synthesis
        justice_analysis = analyze_chief_justice_synthesis(repo_path)
        evidences.append(Evidence(
            detective_name="RepoInvestigator",
            goal="Verify Chief Justice deterministic synthesis logic",
            found="deterministic Python logic" in justice_analysis,
            content=justice_analysis,
            location="src/nodes/justice.py",
            rationale="Deterministic scan for specific Python synthesis rules.",
            confidence=1.0
        ))

        # 8) Safe Tool Engineering
        security_analysis = analyze_security_features(repo_path)
        evidences.append(Evidence(
            detective_name="RepoInvestigator",
            goal="Scan for secure tool engineering and identify 'failure_patterns'",
            found="Uses 'tempfile' for isolated sandboxing" in security_analysis,
            content=security_analysis + "\nVerification: Checking for lack of sandboxing or insecure subprocess calls as per failure_pattern.",
            location="src/tools/repo_tools.py",
            rationale="Forensic scan for both compliance and anti-patterns in tool engineering.",
            confidence=1.0
        ))
        all_files = get_all_repo_files(repo_path)
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
        all_files = []
    
    # Print structured findings for visibility
    for ev in evidences:
        print(f"  [Evidence Found] Goal: {ev.goal[:50]}... | Location: {ev.location} | Confidence: {ev.confidence}")

    return {
        "evidences": {"repo_investigator": evidences},
        "repo_manifest": state.get("repo_manifest", []),
        "hallucinated_paths": []
    }

def doc_analyst(state: AgentState) -> dict:
    """Node: Analyzes documentation and PDFs using RAG-lite."""
    print("--- Detective: DocAnalyst ---")
    from src.tools.doc_tools import ingest_pdf, query_vector_store

    repo_path = state.get("repo_path")
    pdf_path = state.get("pdf_path") or "standard.pdf"
    
    # Try finding the PDF in the cloned repository first
    if repo_path and not os.path.exists(pdf_path):
        repo_pdf = os.path.join(repo_path, pdf_path)
        if os.path.exists(repo_pdf):
            pdf_path = repo_pdf
    
    evidences = []

    try:
        if os.path.exists(pdf_path):
            ingest_pdf(pdf_path)
        else:
            raise FileNotFoundError(f"PDF not found at {pdf_path}")
    except Exception as e:
        print(f"DocAnalyst ingestion warning: {e}")
        evidences.append(Evidence(
            detective_name="DocAnalyst",
            found=False,
            content=str(e),
            location=pdf_path,
            goal="Ingest PDF",
            rationale="Ingestion failed.",
            confidence=0.0
        ))
        return {"evidences": {"doc_analyst": evidences}}

    terms = ["Dialectical Synthesis", "Fan-In / Fan-Out", "Metacognition", "State Synchronization"]
    results = []
    for term in terms:
        results.append(f"**{term}**: {query_vector_store(term)}")

    evidences.append(Evidence(
        detective_name="DocAnalyst",
        goal="Identify both theoretical depth and keyword dropping/missing concepts",
        found=True,
        content=(
            "Analysis of documentation for core theoretical depth:\n"
            + "\n".join(results)
            + "\n\nNote: If any term shows 'No relevant information', it indicates a critical gap or failure to document the theoretical basis."
        ),
        location=pdf_path,
        rationale="Vector search for required theoretical terms, looking for substantive explanations vs buzzword dropping.",
        confidence=0.9
    ))
    return {"evidences": {"doc_analyst": evidences}}

def vision_inspector(state: AgentState) -> dict:
    """Node: Vision analysis of architectural diagrams."""
    print("--- Detective: VisionInspector ---")
    pdf_path = state.get("pdf_path") or ""
    repo_path = state.get("repo_path")
    diag_path = os.path.join(repo_path, "architecture.png") if repo_path else "architecture.png"
    image_paths = extract_images_from_pdf(pdf_path) if pdf_path and os.path.exists(pdf_path) else []
    if not image_paths and os.path.exists(diag_path):
        image_paths = [diag_path]

    import time
    import random
    
    llms = get_detective_llms()
    vision_question = (
        "Analyze this architectural diagram. "
        "1. Identify sections that match the 'success_pattern' (parallel fan-out to Detectives, Aggregation, parallel fan-out to Judges, Chief Justice). "
        "2. Explicitly list any missing elements, linear bottlenecks, or contradictions with the parallel architecture claim. "
        "Be specific about what is NOT there."
    )

    # Small jitter before vision call
    time.sleep(random.uniform(0.5, 2.0))
    for model in llms:
        if not image_paths or "Google" not in model.__class__.__name__:
            continue
        try:
            import base64
            with open(image_paths[0], "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            parts = [
                {"type": "text", "text": vision_question},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
            ]
            resp = model.invoke([HumanMessage(content=parts)])
            return {"evidences": {"vision_inspector": [Evidence(
                detective_name="VisionInspector",
                goal="Analyze diagram",
                found=True,
                content=getattr(resp, "content", str(resp)),
                location=image_paths[0],
                rationale="Vision analysis using Gemini.",
                confidence=0.95
            )]}}
        except Exception:
            continue

    return {"evidences": {"vision_inspector": [Evidence(
        detective_name="VisionInspector",
        goal="Analyze diagram",
        found=True,
        content="Diagram extracted; vision model skipped or unavailable.",
        location="architecture.png",
        rationale="Fallback for non-multimodal environment.",
        confidence=0.5
    )]}}
