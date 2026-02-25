import os
from typing import List, Literal, Any
import statistics
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState, JudicialOpinion, Evidence, CriterionResult, AuditReport

# --- Setup LLM ---
try:
    if "GROQ_API_KEY" in os.environ:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
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
    for source_key, ev_list in state["evidences"].items():
        all_evidence.extend(ev_list)
        
    evidence_text = "\n".join([f"ID: {i}, Detective: {e.detective_name}, Finding: {e.content}, Source: {e.location}" for i, e in enumerate(all_evidence)])
    rubric = state["rubric"]
    
    opinions = []
    # Binding to structured output ensures we get a list of JudicialOpinion objects
    structured_llm = llm.with_structured_output(JudicialOpinion) if llm else None
    
    for criterion_id, details in rubric.get("criteria", {}).items():
        if structured_llm:
            prompt = f"""
            You are the {judge_role}.
            Evaluate the following evidence against the criterion: '{details['name']}' ({details['description']}).
            
            Evidence:
            {evidence_text}
            
            Strictly follow the role-play:
            - Prosecutor: Focus on failures, gaps, and lack of rigor (Trust No One. Assume Vibe Coding).
            - Defense: Highlight strengths, context, and mitigations.
            - TechLead: Focus on practical architecture and "production-grade" engineering.
            
            Output a JudicialOpinion with:
            - judge: {judge_role}
            - criterion_id: {criterion_id}
            - argument: Your specific reasoning
            - cited_evidence: Reference IDs (e.g. ['0', '2']) from the evidence list
            - score: 1-5 (1=Critical Failure, 5=Excellence)
            """
            try:
                opinion = structured_llm.invoke([
                    SystemMessage(content=f"You are a member of the judicial bench: {judge_role}."),
                    HumanMessage(content=prompt)
                ])
                # Ensure the identity matches in case of LLM drift
                opinion.judge = judge_role
                opinion.criterion_id = criterion_id
                opinions.append(opinion)
            except Exception as e:
                print(f"Error getting opinion from {judge_role} for {criterion_id}: {e}")
                opinions.append(JudicialOpinion(
                    judge=judge_role,
                    criterion_id=criterion_id,
                    argument=f"LLM failed to provide opinion: {e}",
                    cited_evidence=[],
                    score=3
                ))
        else:
            opinions.append(JudicialOpinion(
                judge=judge_role,
                criterion_id=criterion_id,
                argument=f"Stub argument for {judge_role} on {criterion_id} (No LLM keys found)",
                cited_evidence=[],
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
    criterion_weights = []
    weighted_scores = []

    for criterion_id, details in rubric.get("criteria", {}).items():
        relevant_ops = [op for op in opinions if op.criterion_id == criterion_id]
        if not relevant_ops:
            continue
            
        # --- DETERMINISTIC RULES ---
        
        # 1. Base Scores
        p_score = next((op.score for op in relevant_ops if op.judge == "Prosecutor"), 3)
        d_score = next((op.score for op in relevant_ops if op.judge == "Defense"), 3)
        t_score = next((op.score for op in relevant_ops if op.judge == "TechLead"), 3)
        
        # 2. TechLead Weighting (Primary score when variance is low, tie-breaker when high)
        computed_score = (p_score + d_score + (2 * t_score)) / 4.0
        
        # 3. Rule: Security Cap & Prosecutor Veto
        is_security = details.get("security", False)
        prosecutor_veto = (p_score <= 1)
        dissent = ""
        
        if is_security and prosecutor_veto:
            computed_score = 1.0
            dissent += "PROSECUTOR VETO APPLIED: Critical security flaw identified. "
        elif is_security and (p_score <= 2 or t_score <= 2):
            computed_score = min(computed_score, 2.0)
            dissent += "Security Cap applied due to severe flags. "
            
        # 4. Rule: Evidence Overrule
        if t_score > 4 and len(next((op.cited_evidence for op in relevant_ops if op.judge == "TechLead"), [])) == 0:
            computed_score = min(computed_score, 3.5) # Penalty for high score without cited evidence

        # 5. Dissent check (variance > 2)
        all_scores = [p_score, d_score, t_score]
        score_range = max(all_scores) - min(all_scores)
        if score_range >= 2:
            dissent += f"Major Variance ({score_range}) detected. "
            if score_range >= 3 and not (is_security and prosecutor_veto):
                dissent += "Tech Lead score prioritized as tie-breaker. "
                computed_score = t_score # Forced tie-break to TechLead
        elif not dissent:
            dissent = "Consensus reached. "
            
        # 6. Rule: Hallucination Penalty
        hallucinated_paths = state.get("hallucinated_paths", [])
        if hallucinated_paths:
            # Check if any judge referenced a hallucinated path in their argument
            if any(any(hp in op.argument for hp in hallucinated_paths) for op in relevant_ops):
                computed_score = min(computed_score, 2.5)
                dissent += "PENALTY: Opinion hallucinated non-existent files. "

        results.append(CriterionResult(
            dimension_id=criterion_id,
            dimension_name=details['name'],
            final_score=computed_score,
            verdict="Pass" if computed_score >= 3.0 else "Fail",
            judge_opinions=relevant_ops,
            dissent_summary=dissent,
            remediation=f"Improve {details['name']} by addressing judge concerns." if computed_score < 3.0 else None
        ))
        
        # Track for overall weighted score
        w = details.get("weight", 1.0)
        criterion_weights.append(w)
        weighted_scores.append(computed_score * w)
        
    # Calculate weighted overall score
    overall_score = sum(weighted_scores) / sum(criterion_weights) if criterion_weights else 0
    
    # Global cap if any security item critically failed
    if any(r.final_score <= 1.0 and r.dimension_id == "safe_tool_engineering" for r in results):
        overall_score = min(overall_score, 2.0)
        results.append(CriterionResult(
            dimension_id="global_security_veto",
            dimension_name="Global Security Veto",
            final_score=1.0,
            verdict="Fail",
            judge_opinions=[],
            dissent_summary="Overall score capped at 2.0 due to critical security failure.",
            remediation="Address the Prosecutor's security veto immediately."
        ))
    
    final_report = AuditReport(
        repo_url=state["repo_url"],
        repo_name=state["repo_url"].split("/")[-1],
        overall_score=overall_score,
        executive_summary=f"Audit completed with an overall score of {overall_score:.2f}.",
        criteria_results=results,
        remediation_plan=[r.remediation for r in results if r.remediation],
        verified_paths=state.get("verified_paths", []),
        hallucinated_paths=state.get("hallucinated_paths", [])
    )
    
    return {"final_report": final_report}
