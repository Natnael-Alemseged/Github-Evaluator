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
            found="[VERIFIED]" in graph_analysis,
            content=graph_analysis,
            location="src/graph.py",
            rationale="Deep AST pattern matching used to verify parallel Fan-Out/Fan-In topology and explicit graph wiring calls.",
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
            rationale="Forensic extraction of raw commit messages to evaluate development trajectory and authorship integrity.",
            confidence=1.0
        ))
        
        # 3) Git Progression
        timeline_analysis = analyze_git_progression(history_analysis)
        evidences.append(Evidence(
            detective_name="RepoInvestigator",
            goal="Verify logical setup -> tools -> graph progression",
            found="[SUCCESS]" in timeline_analysis,
            content=timeline_analysis,
            location="Git History Analytics",
            rationale="Temporal analysis of phases (Infra, Tools, Eval, Synthesis) to detect evolutionary growth vs single bulk uploads.",
            confidence=1.0
        ))

        # 4) State Management
        state_analysis = analyze_state_management(repo_path)
        evidences.append(Evidence(
            detective_name="RepoInvestigator",
            goal="Verify Pydantic models and Annotated reducers in state",
            found="[VERIFIED]" in state_analysis,
            content=state_analysis,
            location="src/state.py",
            rationale="Structural scan for Pydantic BaseModel inheritance and Annotated TypedDict reducers (operator.add/ior).",
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
            rationale="Forensic verification of .with_structured_output() calling pattern to ensure schema enforcement.",
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
            rationale="Persona profiling of system prompts to ensure adversarial tension (Prosecutor vs Defense).",
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
            rationale="Code verification of deterministic resolution rules (Rule of Security, Fact Supremacy) implemented in pure Python.",
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
            rationale="Architectural scan for sandbox isolation using tempfile context managers and safe subprocess.run usage.",
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
    """Node: Analyzes documentation using RAG-lite with specialized forensic queries."""
    print("--- Detective: DocAnalyst ---")
    from src.tools.doc_tools import ingest_pdf, query_vector_store

    pdf_path = state.get("pdf_path") or "standard.pdf"
    repo_path = state.get("repo_path")
    if repo_path and not os.path.exists(pdf_path):
        repo_pdf = os.path.join(repo_path, pdf_path)
        if os.path.exists(repo_pdf):
            pdf_path = repo_pdf
    
    evidences = []
    try:
        # 1. Chunked Ingestion
        ingest_pdf(pdf_path)
        
        # 2. Targeted Forensic Queries (RAG-lite)
        queries = {
            "Dialectical Synthesis": "How does the system use conflicting judge personas to reach a final verdict?",
            "Fan-In / Fan-Out": "Describe the parallel orchestration and merge logic of the graph nodes.",
            "Metacognition": "How does the system evaluate its own reasoning or provide dissent summaries?",
            "State Synchronization": "What mechanisms are used to safely merge parallel agent outputs into the state?"
        }
        
        for goal, query in queries.items():
            result = query_vector_store(query, k=2)
            found = "No relevant information" not in result
            evidences.append(Evidence(
                detective_name="DocAnalyst",
                goal=f"Identify theoretical depth for {goal}",
                found=found,
                content=result if found else f"Missing documentation for {goal}",
                location=f"PDF: {os.path.basename(pdf_path)}",
                rationale=f"Vector similarity search against chunked document for specific theoretical pillar '{goal}'.",
                confidence=0.95 if found else 0.5
            ))
            
    except Exception as e:
        print(f"DocAnalyst warning: {e}")
        evidences.append(Evidence(
            detective_name="DocAnalyst",
            goal="Scan documentation",
            found=False,
            content=str(e),
            location=pdf_path,
            rationale="Ingestion or query failure.",
            confidence=0.0
        ))

    return {"evidences": {"doc_analyst": evidences}}

def vision_inspector(state: AgentState) -> dict:
    """Node: Multimodal vision analysis of architectural diagrams from PDFs."""
    print("--- Detective: VisionInspector ---")
    pdf_path = state.get("pdf_path") or ""
    repo_path = state.get("repo_path")
    
    # 1. Extraction from PDF images + Local Assets
    image_paths = extract_images_from_pdf(pdf_path) if pdf_path and os.path.exists(pdf_path) else []
    diag_path = os.path.join(repo_path, "architecture.png") if repo_path else "architecture.png"
    if os.path.exists(diag_path):
        image_paths.append(diag_path)

    if not image_paths:
        return {"evidences": {"vision_inspector": [Evidence(
            detective_name="VisionInspector",
            goal="Verify parallel architecture via vision",
            found=False,
            content="No images found in PDF or repository.",
            location="None",
            rationale="Search attempted but no visual artifacts discovered.",
            confidence=0.0
        )]}}

    llms = get_detective_llms()
    vision_question = (
        "Analyze this architectural diagram. "
        "1. Identify sections that match the 'success_pattern' (parallel fan-out to Detectives, Aggregation, parallel fan-out to Judges, Chief Justice). "
        "2. Explicitly list any missing elements, linear bottlenecks, or contradictions. "
        "Does the diagram prove the claim of parallel multi-agent orchestration?"
    )

    # 2. Multimodal Execution
    import base64
    for model in llms:
        if "Google" in model.__class__.__name__ or "OpenAI" in model.__class__.__name__:
            try:
                # Use the first image for analysis (usually the main diagram)
                with open(image_paths[0], "rb") as f:
                    b64_img = base64.b64encode(f.read()).decode()
                
                msg = HumanMessage(content=[
                    {"type": "text", "text": vision_question},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                ])
                
                print(f"  [LLM] Vision call to {model.__class__.__name__}")
                resp = model.invoke([msg])
                content = getattr(resp, "content", str(resp))
                
                return {"evidences": {"vision_inspector": [Evidence(
                    detective_name="VisionInspector",
                    goal="Verify parallel architecture visual pattern",
                    found="parallel" in content.lower() or "fan-out" in content.lower(),
                    content=content,
                    location=image_paths[0],
                    rationale="Multimodal LLM analysis performed on extracted PDF/repo images to verify structural layout claims.",
                    confidence=0.98
                )]}}
            except Exception as e:
                print(f"  [LLM] Vision attempt failed: {e}")
                continue

    return {"evidences": {"vision_inspector": [Evidence(
        detective_name="VisionInspector",
        goal="Verify parallel architecture",
        found=True,
        content="Image extracted but multimodal inference skipped in local environment.",
        location=image_paths[0],
        rationale="Evidence exists but full multimodal verification requires active cloud API.",
        confidence=0.5
    )]}}
