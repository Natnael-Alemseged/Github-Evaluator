import json
import os
from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.nodes.detectives import repo_investigator, doc_analyst, vision_inspector
from src.nodes.judges import prosecutor, defense, tech_lead, chief_justice

def load_rubric(state: AgentState) -> dict:
    """Node: Loads the rubric from rubric.json."""
    print("--- Loader: Rubric ---")
    rubric_path = os.path.join(os.path.dirname(__file__), "rubric.json")
    try:
        with open(rubric_path, "r") as f:
            rubric = json.load(f)
        return {"rubric": rubric}
    except Exception as e:
        print(f"Error loading rubric: {e}")
        return {"rubric": {"criteria": {}}}

def evidence_aggregator(state: AgentState) -> dict:
    """Node: Aggregates evidence and prepares for judicial evaluation."""
    print("--- Aggregator: EvidenceAggregator ---")
    # This node primarily acts as a fan-in point before the judge fan-out
    return state

def report_writer(state: AgentState) -> dict:
    """Node: Writes the final report to a Markdown file."""
    print("--- Reporter: MarkdownWriter ---")
    report = state.get("final_report")
    if not report:
        print("No report to write.")
        return state
        
    report_path = "reports/audit_report.md"
    os.makedirs("reports", exist_ok=True)
    
    md_content = f"""# Audit Report: {report.repo_name}
    
## Executive Summary
{report.executive_summary}

## Overall Score: {report.overall_score:.2f} / 5.0

## Detailed Criteria Results
"""
    for res in report.criteria_results:
        md_content += f"""
### {res.dimension_name}
- **Score:** {res.final_score:.2f}
- **Verdict:** {res.verdict}
- **Dissent:** {res.dissent_summary}
- **Justification:** {res.remediation if res.remediation else "No issues found."}
"""
    
    md_content += "\n## Remediation Plan\n"
    for item in report.remediation_plan:
        md_content += f"- {item}\n"
        
    try:
        with open(report_path, "w") as f:
            f.write(md_content)
        print(f"Report written to {report_path}")
    except Exception as e:
        print(f"Failed to write report: {e}")
        
    return state

# --- Graph Definition ---
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("load_rubric", load_rubric)
workflow.add_node("repo_investigator", repo_investigator)
workflow.add_node("doc_analyst", doc_analyst)
workflow.add_node("vision_inspector", vision_inspector)
workflow.add_node("evidence_aggregator", evidence_aggregator)
workflow.add_node("prosecutor", prosecutor)
workflow.add_node("defense", defense)
workflow.add_node("tech_lead", tech_lead)
workflow.add_node("chief_justice", chief_justice)
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

# Fan-out to Judges
workflow.add_edge("evidence_aggregator", "prosecutor")
workflow.add_edge("evidence_aggregator", "defense")
workflow.add_edge("evidence_aggregator", "tech_lead")

# Fan-in to Chief Justice
workflow.add_edge("prosecutor", "chief_justice")
workflow.add_edge("defense", "chief_justice")
workflow.add_edge("tech_lead", "chief_justice")

# Finalize
workflow.add_edge("chief_justice", "report_writer")
workflow.add_edge("report_writer", END)

# Compile
app = workflow.compile()

if __name__ == "__main__":
    import asyncio
    
    async def run_audit():
        print("Starting Automaton Auditor...")
        initial_state = {
            "repo_url": "https://github.com/Natnael-Alemseged/Github-Evaluator",
            "rubric": {},
            "evidences": {},
            "opinions": [],
            "final_report": None
        }
        
        # Using invoke for simplicity in CLI
        result = app.invoke(initial_state)
        
        print("\n--- Audit Complete ---")
        if result.get("final_report"):
            print(f"Overall Score: {result['final_report'].overall_score:.2f}")
    
    asyncio.run(run_audit())
