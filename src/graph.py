from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.nodes.detectives import repo_investigator, doc_analyst

def evidence_aggregator(state: AgentState) -> dict:
    """Node: Aggregates evidence from all parallel detectives."""
    print("--- Aggregator: EvidenceAggregator ---")
    
    all_evidences = state.get("evidences", {})
    total_findings = sum(len(ev_list) for ev_list in all_evidences.values())
    print(f"Aggregated {total_findings} pieces of evidence.")
    
    # TODO: Pass aggregated evidence to Judicial tier
    return state

# --- Graph Definition ---
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("repo_investigator", repo_investigator)
workflow.add_node("doc_analyst", doc_analyst)
workflow.add_node("evidence_aggregator", evidence_aggregator)

# Define edges (Parallel Fan-out)
workflow.add_edge(START, "repo_investigator")
workflow.add_edge(START, "doc_analyst")

# Fan-in to Aggregator
workflow.add_edge("repo_investigator", "evidence_aggregator")
workflow.add_edge("doc_analyst", "evidence_aggregator")

workflow.add_edge("evidence_aggregator", END)

# Compile the graph
app = workflow.compile()

if __name__ == "__main__":
    print("Starting Automaton Auditor...")
    initial_state = {
        "repo_url": "https://github.com/example/repo",
        "rubric": {},
        "evidences": {},
        "opinions": [],
        "final_report": None
    }
    
    # Run the graph
    result = app.invoke(initial_state)
    
    print("\\n--- Final State ---")
    for source, ev_list in result.get("evidences", {}).items():
        for ev in ev_list:
            if hasattr(ev, 'detective_name'):
                print(f"[{source}] {ev.detective_name}: {ev.finding} (Confidence: {ev.confidence})")
            else:
                print(f"[{source}] {ev}")
            
    print("\\nTODO: Implement Judicial layer, synthesis, rubric.json loading, full error handling, and tests.")
