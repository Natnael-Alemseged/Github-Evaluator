import os
from typing import List, Literal, Any
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState, JudicialOpinion, Evidence, CriterionResult, AuditReport

# --- Setup LLM ---
try:
    if "GROQ_API_KEY" in os.environ:
        llm = ChatGroq(model="llama3-70b-8192", temperature=0)
    elif "GOOGLE_API_KEY" in os.environ:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    else:
        llm = None
except Exception:
    llm = None

def get_judge_opinion(judge_role: Literal["Prosecutor", "Defense", "TechLead"], state: AgentState) -> List[JudicialOpinion]:
    """Generic judge logic to evaluate evidence."""
    print(f"--- Judge: {judge_role} ---")
    
    # Flatten all evidence for the judge
    all_evidence = []
    for ev_list in state["evidences"].values():
        all_evidence.extend(ev_list)
        
    evidence_text = "\n".join([f"ID: {i}, Finding: {e.content}, Source: {e.location}" for i, e in enumerate(all_evidence)])
    rubric = state["rubric"]
    
    opinions = []
    structured_llm = llm.with_structured_output(JudicialOpinion) if llm else None
    
    # Process each criterion from the rubric
    for criterion_id, details in rubric.get("criteria", {}).items():
        if structured_llm:
            prompt = f"""
            You are the {judge_role}.
            Evaluate the following evidence against the criterion: '{details['name']}' ({details['description']}).
            
            Evidence:
            {evidence_text}
            
            Output a JudicialOpinion with:
            - judge: {judge_role}
            - criterion_id: {criterion_id}
            - argument: Your specific reasoning as a {judge_role}
            - cited_evidence: Reference IDs from the evidence list
            - score: 1-5 (1=Critical Failure, 5=Excellence)
            """
            opinion = structured_llm.invoke([
                SystemMessage(content=f"You are a member of the judicial bench: {judge_role}."),
                HumanMessage(content=prompt)
            ])
            opinions.append(opinion)
        else:
            # Fallback stub
            opinions.append(JudicialOpinion(
                judge=judge_role,
                criterion_id=criterion_id,
                argument=f"Stub argument for {judge_role} on {criterion_id}",
                cited_evidence=["0"],
                score=3
            ))
            
    return opinions

def prosecutor(state: AgentState) -> dict:
    return {"opinions": get_judge_opinion("Prosecutor", state)}

def defense(state: AgentState) -> dict:
    return {"opinions": get_judge_opinion("Defense", state)}

def tech_lead(state: AgentState) -> dict:
    return {"opinions": get_judge_opinion("TechLead", state)}

def chief_justice(state: AgentState) -> dict:
    """Node: Synthesizes opinions into final results with deterministic rules."""
    print("--- Chief Justice: Synthesis ---")
    opinions = state["opinions"]
    rubric = state["rubric"]
    
    results = []
    for criterion_id, details in rubric.get("criteria", {}).items():
        relevant_ops = [op for op in opinions if op.criterion_id == criterion_id]
        if not relevant_ops:
            continue
            
        # Deterministic Rules
        scores = [op.score for op in relevant_ops]
        avg_score = sum(scores) / len(scores)
        
        # Rule: Security Cap (if TechLead scores < 2 on a security item, cap avg at 2)
        # TODO: Implement metadata-based caps
        
        # Rule: Dissent check (variance > 2)
        score_range = max(scores) - min(scores)
        dissent = f"Variance of {score_range} detected." if score_range >= 2 else "Consensus reached."
        
        results.append(CriterionResult(
            dimension_id=criterion_id,
            dimension_name=details['name'],
            final_score=avg_score,
            verdict="Pass" if avg_score >= 3.0 else "Fail",
            judge_opinions=relevant_ops,
            dissent_summary=dissent,
            remediation=f"Improve {details['name']} by addressing judge concerns." if avg_score < 3.0 else None
        ))
        
    overall_score = sum(r.final_score for r in results) / len(results) if results else 0
    
    # Final Report Assembly
    final_report = AuditReport(
        repo_url=state["repo_url"],
        repo_name=state["repo_url"].split("/")[-1],
        overall_score=overall_score,
        executive_summary=f"Audit completed with an overall score of {overall_score:.2f}.",
        criteria_results=results,
        remediation_plan=[r.remediation for r in results if r.remediation]
    )
    
    return {"final_report": final_report}
