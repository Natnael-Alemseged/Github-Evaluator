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
from langchain_openai import ChatOpenAI
from src.tools.doc_tools import extract_images_from_pdf

# --- Setup LLM Fallback ---
llms = []
if "GROQ_API_KEY" in os.environ:
    llms.append(ChatGroq(model="llama-3.3-70b-versatile", temperature=0))
if "OPENROUTER_KEY" in os.environ:
    # Use highly available free model on OpenRouter for detectives
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


def repo_investigator(state: AgentState) -> dict:
    """Node: Investigates the repository structure and code."""
    print("--- Detective: RepoInvestigator ---")
    repo_url = state["repo_url"]
    
    evidences = []
    try:
        with RepoSandbox(repo_url) as repo_path:
            print(f"--- RepoInvestigator Analyzing: {repo_path} ---")
            
            # 1) Analysis of Graph Structure
            graph_analysis = analyze_graph_structure(repo_path)
            print(f"  [1] Graph Structure found: {len(graph_analysis)} chars")
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
            print(f"  [2] History Analysis found: {len(history_analysis)} chars")
            evidences.append(Evidence(
                detective_name="RepoInvestigator",
                goal="Retrieve git history for effort and atomic commits",
                found=len(history_analysis) > 50,
                content=history_analysis,
                location="Git Log",
                rationale="Used to gauge developer effort and commit quality.",
                confidence=1.0
            ))
            
            # 3) Git Progression (Timeline)
            git_history = extract_git_history(repo_path)
            timeline_analysis = analyze_git_progression(git_history)
            print(f"  [3] Timeline Analysis found: {len(timeline_analysis)} chars")
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
            print(f"  [4] State Management found: {len(state_analysis)} chars")
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
            print(f"  [5] Structured Output found: {len(output_analysis)} chars")
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
            print(f"  [6] Judicial Nuance found: {len(nuance_analysis)} chars")
            evidences.append(Evidence(
                detective_name="RepoInvestigator",
                goal="Verify distinct persona instructions (Prosecutor, Defense, Tech Lead)",
                found="Three distinct personas defined" in nuance_analysis,
                content=nuance_analysis,
                location="src/nodes/judges.py",
                rationale="Keyword scan for persona-specific system prompt instructions.",
                confidence=1.0
            ))
            
            # 7) Chief Justice Synthesis
            justice_analysis = analyze_chief_justice_synthesis(repo_path)
            print(f"  [7] Chief Justice found: {len(justice_analysis)} chars")
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
            print(f"  [8] Security Analysis found: {len(security_analysis)} chars")
            evidences.append(Evidence(
                detective_name="RepoInvestigator",
                goal="Scan for secure tool engineering",
                found="Uses 'tempfile' for isolated sandboxing" in security_analysis,
                content=security_analysis,
                location="src/tools/repo_tools.py",
                rationale="Scan for subprocess safety and temporary directory sandboxing.",
                confidence=1.0
            ))
            
            # Emit raw list of actual files for hallucination checking
            all_files = get_all_repo_files(repo_path)
            print(f"  [9] Manifest found: {len(all_files)} files")
            
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
    
    return {
        "evidences": {"repo_investigator": evidences},
        "repo_manifest": all_files,
        "hallucinated_paths": []
    }

def doc_analyst(state: AgentState) -> dict:
    """Node: Analyzes documentation and PDFs using RAG-lite (chunked, no full dump)."""
    print("--- Detective: DocAnalyst ---")
    from src.tools.doc_tools import ingest_pdf, query_vector_store

    pdf_path = state.get("pdf_path") or "standard.pdf"
    evidences = []

    try:
        ingest_pdf(pdf_path)
    except Exception as e:
        print(f"DocAnalyst ingestion warning: {e}")
        evidences.append(Evidence(
            detective_name="DocAnalyst",
            goal="Ingest PDF for RAG query",
            found=False,
            content=str(e),
            location=pdf_path,
            rationale="PDF ingestion failed.",
            confidence=0.0
        ))
        return {"evidences": {"doc_analyst": evidences}}

    # Rubric Protocol A.2: Keyword search for all four theoretical-depth terms and context check
    THEORETICAL_DEPTH_TERMS = [
        "Dialectical Synthesis",
        "Fan-In / Fan-Out",
        "Metacognition",
        "State Synchronization",
    ]
    ARCHITECTURAL_KEYWORDS = (
        "graph", "edge", "node", "parallel", "fan-out", "fan-in", "fan_out", "fan_in",
        "implement", "orchestration", "StateGraph", "reducer", "aggregator",
        "synchronization", "persona", "judge", "detective", "dialectical",
    )
    BUZZWORD_INDICATORS = ("executive summary", "we use", "our system uses", "the report describes")

    theoretical_findings: List[dict] = []
    for term in THEORETICAL_DEPTH_TERMS:
        snippet = query_vector_store(term)
        if (not snippet or "not found" in (snippet or "").lower()) and term == "Fan-In / Fan-Out":
            snip_in = query_vector_store("Fan-In")
            snip_out = query_vector_store("Fan-Out")
            snippet = ((snip_in or "") + "\n" + (snip_out or "")).strip() if (snip_in or snip_out) else snippet
        found = bool(snippet and "not found" not in snippet.lower() and snippet.strip())
        if not found:
            theoretical_findings.append({
                "term": term,
                "found": False,
                "context": "not_present",
                "sentences": "",
            })
            continue
        snippet_lower = snippet.lower()
        in_architectural = any(kw in snippet_lower for kw in ARCHITECTURAL_KEYWORDS)
        looks_buzzword = (
            len(snippet.strip()) < 120
            or any(phrase in snippet_lower for phrase in BUZZWORD_INDICATORS)
        ) and not in_architectural
        context = "architectural_explanation" if in_architectural else ("buzzword_or_executive_summary" if looks_buzzword else "substantive_section")
        # Capture first 400 chars as the specific sentences detailing the concept
        sentences = snippet.strip()[:400] + ("..." if len(snippet.strip()) > 400 else "")
        theoretical_findings.append({
            "term": term,
            "found": True,
            "context": context,
            "sentences": sentences,
        })

    theoretical_summary = "\n\n".join(
        f"**{f['term']}**: {'Found' if f['found'] else 'Not found'}"
        + (f" — Context: {f['context']}. Sentences: {f['sentences']}" if f.get("sentences") else "")
        for f in theoretical_findings
    )
    evidences.append(Evidence(
        detective_name="DocAnalyst",
        goal="Theoretical Depth: search for 'Dialectical Synthesis', 'Fan-In / Fan-Out', 'Metacognition', 'State Synchronization' and capture if in architectural explanation or buzzword",
        found=any(f["found"] for f in theoretical_findings),
        content=theoretical_summary,
        location=f"{pdf_path} (Vector Search — theoretical depth keywords)",
        rationale="RAG keyword search per rubric; context check distinguishes architectural explanations from executive-summary buzzwords.",
        confidence=0.95
    ))

    # General architecture/dependency compliance query (existing behavior)
    query = "What does the report say about Dialectical Synthesis?"
    findings_query = query
    rubric_dimensions = state.get("rubric_dimensions", [])
    for dim in rubric_dimensions:
        if dim.get("target_artifact") == "report" or (dim.get("target_artifact") or "").lower().find("report") >= 0:
            findings_query = dim.get("forensic_instruction") or query
            break

    finding_content = query_vector_store(findings_query)

    evidences.append(Evidence(
        detective_name="DocAnalyst",
        goal="Check for architecture and dependency compliance in documentation",
        found=bool(finding_content and "not found" not in finding_content.lower()),
        content=finding_content or "No relevant information found in documentation.",
        location=f"{pdf_path} (Vector Search)",
        rationale="RAG-lite query over chunked PDF; verified against documentation.",
        confidence=0.95
    ))
    return {"evidences": {"doc_analyst": evidences}}

def vision_inspector(state: AgentState) -> dict:
    """Node: Vision analysis of architectural diagrams (multimodal detective).
    Implements extract_images_from_pdf(path) and passes images to vision model with:
    'Is this a StateGraph diagram or a generic box diagram?' Running vision to get results is optional."""
    print("--- Detective: VisionInspector ---")
    evidence = None
    pdf_path = state.get("pdf_path") or ""
    diag_path = "architecture.png"

    # 1) Extract images from PDF per doc (VisionInspector task)
    image_paths = extract_images_from_pdf(pdf_path) if pdf_path and os.path.exists(pdf_path) else []
    if not image_paths and os.path.exists(diag_path):
        image_paths = [diag_path]

    vision_question = "Is this a StateGraph diagram or a generic box diagram? Does it show parallel fan-out to detectives/judges and fan-in to an aggregator?"

    # 2) Optionally pass to multimodal LLM (running to get results is optional per doc)
    for model in llms:
        if not image_paths:
            break
        # Only attempt multimodal for Gemini or specify proper vision model
        if "Google" not in model.__class__.__name__:
            continue
            
        try:
            # Prefer a model that supports images (e.g. Gemini)
            if hasattr(model, "bind") and image_paths:
                from langchain_core.messages import HumanMessage
                parts = [{"type": "text", "text": vision_question}]
                for p in image_paths[:3]:
                    if os.path.exists(p):
                        try:
                            with open(p, "rb") as f:
                                import base64
                                b64 = base64.b64encode(f.read()).decode()
                            parts.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
                        except Exception:
                            continue
                if len(parts) > 1:
                    resp = model.invoke([HumanMessage(content=parts)])
                    content = getattr(resp, "content", str(resp))
                    evidence = Evidence(
                        detective_name="VisionInspector",
                        goal="Analyze architectural diagrams for pipeline correctness",
                        found=True,
                        content=f"Multimodal Vision Analysis: {content}",
                        location=f"{pdf_path or diag_path} (Vision Scan)",
                        rationale="Vision model asked: " + vision_question,
                        confidence=0.95
                    )
                    break
        except Exception as e:
            print(f"VisionInspector vision model skip: {e}")
            continue

    if evidence is None:
        if image_paths:
            evidence = Evidence(
                detective_name="VisionInspector",
                goal="Analyze architectural diagrams for pipeline correctness",
                found=True,
                content="Images extracted from PDF/repo; vision model not invoked or unavailable (optional per spec).",
                location=f"{pdf_path or diag_path}",
                rationale="extract_images_from_pdf implemented; running vision to get results is optional.",
                confidence=0.7
            )
        else:
            evidence = Evidence(
                detective_name="VisionInspector",
                goal="Analyze architectural diagrams",
                found=False,
                content="No architecture diagram or PDF images found. Cannot verify visual alignment.",
                location="N/A",
                rationale="Missing architecture.png and no images from PDF.",
                confidence=1.0
            )

    return {"evidences": {"vision_inspector": [evidence]}}
