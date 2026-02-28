import json
import os
from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.nodes.detectives import repo_investigator, doc_analyst, vision_inspector
from src.nodes.judges import prosecutor, defense, tech_lead
from src.nodes.justice import chief_justice_node

def load_rubric(state: AgentState) -> dict:
    """Node: Loads the rubric from rubric.json."""
    print("--- Loader: Rubric ---")
    rubric_path = os.path.join(os.path.dirname(__file__), "rubric.json")
    try:
        with open(rubric_path, "r") as f:
            rubric_data = json.load(f)
        # The guide expects a list of dimensions
        dimensions = rubric_data.get("dimensions", [])
        return {"rubric_dimensions": dimensions}
    except Exception as e:
        print(f"Error loading rubric: {e}")
        return {"rubric_dimensions": []}

def evidence_aggregator(state: AgentState) -> dict:
    """Aggregates evidence and performs hallucination checks."""
    print("--- Aggregator: EvidenceAggregator ---")
    import re
    
    verified = set()
    hallucinated = set()
    
    # More robust regex for paths with specific extensions to avoid catching version numbers
    path_pattern = re.compile(r'\b[\w\-\./]+\.(?:py|md|json|pdf|png|toml|yaml|txt|js|ts|yml|env\.example|sh|lock)\b')
    repo_files = set(state.get("repo_manifest", []))
    
    # Always allow some stubs for the interim
    repo_files.update(['standard.pdf', 'architecture.png'])
    
    for ev_list in state.get("evidences", {}).values():
        for ev in ev_list:
            # Guard against None content (Evidence.content is Optional[str])
            content_text = ev.content or ""
            potential_paths = path_pattern.findall(ev.location) + path_pattern.findall(content_text)
            for p in potential_paths:
                clean_p = p.lstrip('./').lstrip('/')
                    
                # Exact match or suffix match (e.g. src/graph.py matches graph.py if it's unique)
                is_verified = False
                for rf in repo_files:
                    if clean_p == rf or clean_p.endswith('/' + rf) or rf.endswith('/' + clean_p):
                        verified.add(rf)
                        is_verified = True
                        break
                
                if not is_verified:
                    # Only add if it's not a known allowed stub and not a false positive
                    hallucinated.add(clean_p)
                        
    return {
        "verified_paths": list(verified),
        "hallucinated_paths": list(hallucinated)
    }

def judges_entry(state: AgentState) -> dict:
    """No-op fan-out hub: pass-through to allow conditional routing to judges."""
    return {}

def evidence_router(state: AgentState) -> str:
    """Conditional Edge: Route to Judgement or skip if no evidence found."""
    all_ev = state.get("evidences", {})
    # Flatten all evidence lists
    total_findings = sum(len(ev_list) for ev_list in all_ev.values())
    
    # If no real findings (excluding placeholders with 0 confidence or specifically marked)
    # For this interim, we check if total_findings > 0
    if total_findings == 0:
        print("!!! No evidence detected. Routing to final report writer directly.")
        return "skip_to_report"
    
    return "continue_to_judges"

def report_writer(state: AgentState) -> dict:
    """Node: Writes the final report to a Markdown file.
    Structure: Executive Summary -> Criterion Breakdown -> Remediation Plan (no console print).
    """
    print("--- Reporter: MarkdownWriter ---")
    report = state.get("final_report")
    report_path = "audit/report_onself_generated/report.md"
    os.makedirs("audit/report_onself_generated", exist_ok=True)
    
    if not report:
        print("No report to write (e.g. audit skipped due to no evidence). Writing minimal report.")
        try:
            with open(report_path, "w") as f:
                f.write("# Audit Report\n\nNo evidence was collected. Audit skipped. Check detective nodes or repo URL.\n")
            print(f"Report written to {report_path}")
        except Exception as e:
            print(f"Failed to write report: {e}")
        return state
    
    md_content = f"""# Audit Report: {report.repo_name or 'Repository'}

## Executive Summary

{report.executive_summary}

## Criterion Breakdown

### Evidence Integrity
- **Repo Manifest:** {len(state.get('repo_manifest', []))} files scanned from the repository.
- **Verified Paths (cited in evidence):** {', '.join(sorted(set(report.verified_paths))) if report.verified_paths else 'None'}
- **Hallucinated Paths (cited but not in repo):** {', '.join(sorted(set(report.hallucinated_paths))) if report.hallucinated_paths else 'None ✅'}

### Overall Score: {report.overall_score:.2f} / 5.0

### Score Summary

| Dimension | Prosecutor | Defense | TechLead | Final | Verdict |
|-----------|:----------:|:-------:|:--------:|:-----:|:-------:|
"""
    for res in report.criteria:
        p_score = next((op.score for op in res.judge_opinions if op.judge == "Prosecutor"), "—")
        d_score = next((op.score for op in res.judge_opinions if op.judge == "Defense"), "—")
        t_score = next((op.score for op in res.judge_opinions if op.judge == "TechLead"), "—")
        verdict = "Pass" if res.final_score >= 3 else "Fail"
        md_content += f"| {res.dimension_name} | {p_score} | {d_score} | {t_score} | **{res.final_score}** | {verdict} |\n"

    md_content += "\n### Dimension Details\n"
    for res in report.criteria:
        verdict = "Pass" if res.final_score >= 3 else "Fail"
        md_content += f"""
#### {res.dimension_name}
- **Final Score:** {res.final_score} / 5
- **Verdict:** {verdict}
- **Dissent / Notes:** {res.dissent_summary if res.dissent_summary else "Consensus reached."}
- **Remediation:** {res.remediation if res.remediation else "No issues found."}
"""
        for op in res.judge_opinions:
            arg_text = getattr(op, "argument", "")
            md_content += f"  - **{op.judge}** (score {op.score}): {arg_text}\n"

    md_content += "\n## Remediation Plan\n\n"
    md_content += report.remediation_plan + "\n"
        
    try:
        with open(report_path, "w") as f:
            f.write(md_content)
        print(f"Report written to {report_path}")
    except Exception as e:
        print(f"Failed to write report: {e}")
        
    return state

# --- Graph Definition ---
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# Use a persistent SQLite DB for checkpointer
# In a real app, this would be a file path like 'checkpoints.db'
conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
memory = SqliteSaver(conn)

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("load_rubric", load_rubric)
workflow.add_node("repo_investigator", repo_investigator)
workflow.add_node("doc_analyst", doc_analyst)
workflow.add_node("vision_inspector", vision_inspector)
workflow.add_node("evidence_aggregator", evidence_aggregator)
workflow.add_node("judges_entry", judges_entry)
workflow.add_node("prosecutor", prosecutor)
workflow.add_node("defense", defense)
workflow.add_node("tech_lead", tech_lead)
workflow.add_node("chief_justice", chief_justice_node)
workflow.add_node("report_writer", report_writer)

# Define edges
workflow.add_edge(START, "load_rubric")

# Fan-out to Detectives
workflow.add_edge("load_rubric", "repo_investigator")
workflow.add_edge("load_rubric", "doc_analyst")
workflow.add_edge("load_rubric", "vision_inspector")

# Fan-in to Aggregator
workflow.add_edge("repo_investigator", "evidence_aggregator")
workflow.add_edge("doc_analyst", "evidence_aggregator")
workflow.add_edge("vision_inspector", "evidence_aggregator")

# Conditional Routing after Aggregator (only one path: judges OR report)
workflow.add_conditional_edges(
    "evidence_aggregator",
    evidence_router,
    {
        "continue_to_judges": "judges_entry",
        "skip_to_report": "report_writer"
    }
)

# Fan-out from judges entry to all three judges (no unconditional edges from aggregator)
workflow.add_edge("judges_entry", "prosecutor")
workflow.add_edge("judges_entry", "defense")
workflow.add_edge("judges_entry", "tech_lead")

# Fan-in to Chief Justice
workflow.add_edge("prosecutor", "chief_justice")
workflow.add_edge("defense", "chief_justice")
workflow.add_edge("tech_lead", "chief_justice")

# Finalize
workflow.add_edge("chief_justice", "report_writer")
workflow.add_edge("report_writer", END)

# Compile with checkpointer
app = workflow.compile(checkpointer=memory)

if __name__ == "__main__":
    import asyncio
    import uuid
    from src.tools.doc_tools import clear_vector_store
    from src.tools.repo_tools import is_safe_url
    
    async def run_audit():
        import sys
        print("Starting Automaton Auditor...")
        clear_vector_store()
        
        default_repo = "https://github.com/Natnael-Alemseged/Github-Evaluator"
        repo_url = sys.argv[1] if len(sys.argv) > 1 else default_repo
        
        print(f"✅ Target Repo: {repo_url}")
        
        run_id = f"audit_{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": run_id}}
        
        initial_state = {
            "repo_url": repo_url,
            "pdf_path": "interim_report.pdf", # Report to cross-reference
            "rubric_dimensions": [],
            "evidences": {},
            "opinions": [],
            "repo_path": None,
            "verified_paths": [],
            "hallucinated_paths": [],
            "repo_manifest": [],
            "final_report": None
        }
        
        try:
            # Synchronous invoke within async wrapper
            result = app.invoke(initial_state, config=config)
            print("\n--- Audit Complete ---")
            if result.get("final_report"):
                print(f"Overall Score: {result['final_report'].overall_score:.2f}/5.0")
        except Exception as e:
            print(f"\n❌ Execution failed: {e}")
            print("Note: The repository might be private or inaccessible. Ensure the URL is public and correct.")
    
    asyncio.run(run_audit())
