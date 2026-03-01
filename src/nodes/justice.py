"""
Phase 4: The Supreme Court & Feedback Loop.
ChiefJusticeNode: Deterministic conflict resolution and report synthesis.
Output: AuditReport consumed by report_writer → Markdown file (Executive Summary → Criterion Breakdown → Remediation Plan).
"""

import json
import os
import time
import random
from typing import Dict, List, Optional, Tuple

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

from src.state import (
    AgentState,
    AuditReport,
    CriterionResult,
    Evidence,
    JudicialOpinion,
)

def get_justice_llm():
    """Returns LLMs for Layer 3 (Justice). Primary: SambaNova, Fallback: OpenRouter."""
    llms = []
    if os.environ.get("SAMBANOVA_KEY"):
        llms.append(ChatOpenAI(
            model="Meta-Llama-3.3-70B-Instruct", # Use Llama 3.3 70B for fast accurate synthesis
            openai_api_key=os.environ["SAMBANOVA_KEY"],
            openai_api_base="https://api.sambanova.ai/v1",
            temperature=0,
            request_timeout=30
        ))
    
    if os.environ.get("OPENROUTER_KEY"):
         llms.append(ChatOpenAI(
            model="openai/gpt-4o-mini",
            openai_api_key=os.environ["OPENROUTER_KEY"],
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0
        ))
         
    # Ollama as absolute last resort
    llms.append(ChatOpenAI(
        model="llama3.1", 
        openai_api_key="ollama", 
        openai_api_base="http://localhost:11434/v1",
        temperature=0
    ))
    return llms


# ---------------------------------------------------------------------------
# Conflict Resolution Strategy (hardcoded deterministic Python logic)
# Driven by rubric.json synthesis_rules; no LLM averaging.
# ---------------------------------------------------------------------------

def _load_synthesis_rules() -> Dict:
    """Load synthesis_rules from rubric.json for variance and rule configuration."""
    rubric_path = os.path.join(os.path.dirname(__file__), "..", "rubric.json")
    try:
        with open(rubric_path, "r") as f:
            data = json.load(f)
        return data.get("synthesis_rules", {})
    except Exception:
        return {}


def _get_all_evidence(state: AgentState) -> List[Evidence]:
    """Flatten all evidence from state for re-evaluation checks."""
    evidences = state.get("evidences", {}) or {}
    out = []
    for ev_list in evidences.values():
        out.extend(ev_list)
    return out


def _citation_ids_to_evidence_index(citations: List[str]) -> List[int]:
    """Convert citation IDs (e.g. '0', '2') to integer indices for evidence lookup."""
    indices = []
    for c in citations or []:
        try:
            indices.append(int(c))
        except (ValueError, TypeError):
            continue
    return indices


def _re_evaluate_evidence_for_variance(
    state: AgentState,
    relevant_ops: List[JudicialOpinion],
    all_evidence: List[Evidence],
) -> Tuple[int, int, int, str]:
    """
    When score variance > 2, re-evaluate specific evidence per rubric synthesis_rules.variance_re_evaluation.
    Deterministic: check which judge's citations are supported by actual evidence; then resolve score.
    Returns (p_score, d_score, t_score, re_eval_notes).
    """
    p_score = next((op.score for op in relevant_ops if op.judge == "Prosecutor"), 3)
    d_score = next((op.score for op in relevant_ops if op.judge == "Defense"), 3)
    t_score = next((op.score for op in relevant_ops if op.judge == "TechLead"), 3)
    notes = []

    # Defense: if high score but cited evidence missing or weak → overrule (Rule of Evidence)
    defense_op = next((op for op in relevant_ops if op.judge == "Defense"), None)
    if defense_op and d_score >= 4:
        cites = getattr(defense_op, "cited_evidence", [])
        indices = _citation_ids_to_evidence_index(cites)
        supported = sum(1 for i in indices if 0 <= i < len(all_evidence) and (all_evidence[i].content or "").strip())
        if not indices or supported < len(indices) / 2:
            d_score = min(d_score, 3)
            notes.append("Defense overruled: cited evidence not sufficiently supported by Detective findings.")

    # Prosecutor: if low score and cited evidence confirms flaw → keep; else no change
    prosecutor_op = next((op for op in relevant_ops if op.judge == "Prosecutor"), None)
    if prosecutor_op and p_score <= 2:
        cites = getattr(prosecutor_op, "cited_evidence", [])
        indices = _citation_ids_to_evidence_index(cites)
        if indices and any(0 <= i < len(all_evidence) for i in indices):
            notes.append("Prosecutor evidence re-verified against Detective evidence.")

    # Tech Lead: if high score with no citations → slight penalty (already in main logic)
    tech_op = next((op for op in relevant_ops if op.judge == "TechLead"), None)
    if tech_op and t_score >= 4:
        cites = getattr(tech_op, "cited_evidence", [])
        if not cites:
            t_score = min(t_score, 4)
            notes.append("Tech Lead score capped: no cited evidence.")

    return p_score, d_score, t_score, " ".join(notes)


def _apply_security_override(
    criterion_id: str,
    p_score: int,
    computed_score: float,
    dissent: List[str],
    synthesis_rules: Dict,
) -> Tuple[float, List[str]]:
    """Rule of Security: confirmed vulnerabilities cap score at 3 (per rubric)."""
    security_dimensions = {"safe_tool_engineering", "structured_output_enforcement"}
    if criterion_id not in security_dimensions:
        return computed_score, dissent
    rule = synthesis_rules.get("security_override", "")
    if p_score <= 1 and "cap" in rule.lower():
        dissent.append("SECURITY OVERRIDE: Prosecutor identified confirmed vulnerability; score capped at 3.")
        return min(computed_score, 3.0), dissent
    if p_score <= 2:
        dissent.append("Security concern: Prosecutor flagged significant risk; score capped at 3.")
        return min(computed_score, 3.0), dissent
    return computed_score, dissent


def _apply_fact_supremacy(
    criterion_id: str,
    d_score: int,
    computed_score: float,
    dissent: List[str],
    all_evidence: List[Evidence],
    defense_op: Optional[JudicialOpinion],
) -> Tuple[float, List[str]]:
    """Rule of Evidence: Defense overruled if claims lack Detective evidence."""
    if not defense_op or d_score < 4:
        return computed_score, dissent
    arg_text = getattr(defense_op, "argument", "")
    if "metacognition" in arg_text.lower() or "deep" in arg_text.lower():
        # Check if any evidence supports this
        content_combined = " ".join((e.content or "") for e in all_evidence).lower()
        if "metacognition" not in content_combined and "evaluat" not in content_combined:
            dissent.append("FACT SUPREMACY: Defense claim not supported by Detective evidence; Defense overruled.")
            return min(computed_score, 3.0), dissent
    return computed_score, dissent


def _apply_functionality_weight(
    criterion_id: str,
    t_score: int,
    p_score: int,
    d_score: int,
    synthesis_rules: Dict,
) -> float:
    """Rule of Functionality: Tech Lead confirmation carries highest weight for architecture criterion."""
    if criterion_id != "graph_orchestration":
        return (p_score + d_score + t_score) / 3.0
    rule = synthesis_rules.get("functionality_weight", "")
    if "tech lead" in rule.lower() and "highest weight" in rule.lower() and t_score >= 4:
        # Tech Lead confirms modular/workable → weight Tech Lead more
        return (p_score + d_score + 2.0 * t_score) / 4.0
    return (p_score + d_score + t_score) / 3.0


def chief_justice_node(state: AgentState) -> dict:
    """
    ChiefJusticeNode: Synthesize conflict and operationalize the swarm.
    - Conflict Resolution Strategy: hardcoded deterministic rules from rubric.
    - If variance in scores > 2: trigger re-evaluation of specific evidence per JSON config.
    - Output: state update with final_report (Markdown is produced by report_writer).
    """
    print("--- Chief Justice: Synthesis (Conflict Resolution) ---")
    opinions = state.get("opinions", [])
    rubric_dimensions = state.get("rubric_dimensions", [])
    synthesis_rules = _load_synthesis_rules()
    all_evidence = _get_all_evidence(state)

    results: List[CriterionResult] = []
    criterion_weights: List[float] = []
    weighted_scores: List[float] = []

    for dimension in rubric_dimensions:
        criterion_id = dimension.get("id", "")
        dimension_name = dimension.get("name", criterion_id)
        relevant_ops = [op for op in opinions if op.criterion_id == criterion_id]
        if not relevant_ops:
            continue

        p_score = next((op.score for op in relevant_ops if op.judge == "Prosecutor"), 3)
        d_score = next((op.score for op in relevant_ops if op.judge == "Defense"), 3)
        t_score = next((op.score for op in relevant_ops if op.judge == "TechLead"), 3)

        variance = max(p_score, d_score, t_score) - min(p_score, d_score, t_score)
        dissent: List[str] = []
        re_eval_notes = ""

        # Variance > 2: re-evaluate specific evidence per synthesis_rules
        if variance > 2 and synthesis_rules.get("variance_re_evaluation"):
            p_score, d_score, t_score, re_eval_notes = _re_evaluate_evidence_for_variance(
                state, relevant_ops, all_evidence
            )
            dissent.append(f"Major variance ({variance}) triggered evidence re-evaluation. {re_eval_notes}")

        # Base score: deterministic combination
        computed_score = _apply_functionality_weight(
            criterion_id, t_score, p_score, d_score, synthesis_rules
        )

        # Rule of Security
        computed_score, dissent = _apply_security_override(
            criterion_id, p_score, computed_score, dissent, synthesis_rules
        )

        # Rule of Evidence (fact supremacy)
        defense_op = next((op for op in relevant_ops if op.judge == "Defense"), None)
        computed_score, dissent = _apply_fact_supremacy(
            criterion_id, d_score, computed_score, dissent, all_evidence, defense_op
        )

        # Dissent requirement: every criterion with variance > 2 must have a meaningful dissent summary
        if variance > 2:
            dissent_reasons = []
            for op in relevant_ops:
                dissent_reasons.append(f"{op.judge} (score {op.score}): {op.argument[:100]}...")
            dissent.append(f"DISSENT SUMMARY: Significant variance ({variance}) detected. " + " | ".join(dissent_reasons))
        elif not dissent:
            dissent.append("Consensus reached.")

        # Hallucination penalty
        hallucinated_paths = state.get("hallucinated_paths", []) or []
        for op in relevant_ops:
            arg_text = getattr(op, "argument", "")
            if any(hp in arg_text for hp in hallucinated_paths):
                computed_score = min(computed_score, 2.5)
                dissent.append("PENALTY: Opinion referenced hallucinated (non-existent) paths.")
                break

        # Graph orchestration: Prosecutor flag for linear flow
        if criterion_id == "graph_orchestration" and p_score <= 2:
            computed_score = min(computed_score, 2.5)
            dissent.append("PROSECUTOR FLAG: Potential linear flow or orchestration weakness.")

        final_score = max(1, min(5, int(round(computed_score))))
        
        # PROSECUTOR FLOOR: Prevent 'grade inflation' if Prosecutor flags major failure
        if p_score <= 2:
            strict_limit = p_score + 1
            if final_score > strict_limit:
                final_score = strict_limit
                msg = f"  [Chief Justice] PROSECUTOR FLOOR applied to {criterion_id}: Cap {strict_limit}"
                print(msg)
                dissent.append(f"PROSECUTOR FLOOR: Final score capped at {strict_limit} due to Prosecutor's adversarial finding (score {p_score}).")

        # Concrete remediation: If score < 5, try to be specific
        if final_score < 5:
            worst_judge = min(relevant_ops, key=lambda x: x.score)
            remediation = f"Address concern from {worst_judge.judge}: {worst_judge.argument[:150]}..."
        else:
            remediation = "No issues found."

        results.append(
            CriterionResult(
                dimension_id=criterion_id,
                dimension_name=dimension_name,
                final_score=final_score,
                judge_opinions=relevant_ops,
                dissent_summary=" ".join(dissent).strip() or None,
                remediation=remediation,
            )
        )

        w = dimension.get("weight", 1.0)
        criterion_weights.append(w)
        weighted_scores.append(computed_score * w)

    # Overall score
    overall_score = (
        sum(weighted_scores) / sum(criterion_weights) if criterion_weights else 0.0
    )

    # Global security veto
    if any(
        r.final_score <= 1 and r.dimension_id == "safe_tool_engineering" for r in results
    ):
        overall_score = min(overall_score, 2.0)
        results.append(
            CriterionResult(
                dimension_id="global_security_veto",
                dimension_name="Global Security Veto",
                final_score=1,
                judge_opinions=[],
                dissent_summary="Overall score capped due to critical security failure (Prosecutor veto).",
                remediation="Address security vulnerability in tool/repo handling immediately.",
            )
        )

    # Executive summary
    passed = [r for r in results if r.final_score >= 3]
    failed = [r for r in results if r.final_score < 3]
    summary_lines = [
        f"Overall Score: {overall_score:.2f}/5.0",
        f"Dimensions: {len(results)} | Passed: {len(passed)} | Failed: {len(failed)}",
    ]
    if failed:
        summary_lines.append(f"Critical Failures: {', '.join(r.dimension_name for r in failed)}")
    
    hallucinated_paths = state.get("hallucinated_paths", []) or []
    verified_paths = state.get("verified_paths", []) or []
    repo_manifest = state.get("repo_manifest", []) or []
    
    summary_lines.append(f"Evidence Integrity: {len(hallucinated_paths)} hallucinations, {len(verified_paths)} verified files.")
    executive_summary = "\n".join(summary_lines)

    # Compile criterion-level remediation for the LLM
    detailed_remediation_context = "\n".join(
        f"- {r.dimension_name} (Score {r.final_score}): {r.remediation}"
        for r in results if r.final_score < 5
    ) or "Everything is optimal."

    # Metacognition: LLM Polish for Executive Summary and Remediation Plan
    print("  [Justice] LLM Synthesis starting (Layer 3)...")
    time.sleep(1.0)
    
    from src.state import JusticeOutput 
    justice_llms = get_justice_llm()
    executive_summary_final = executive_summary
    remediation_plan_final = detailed_remediation_context

    prompt = f"""
    You are the Chief Justice. Review the deterministic summary and the detailed remediation context.
    Polish them into a professional, cohesive, and insightful narrative report.
    
    CRITICAL REQUIREMENTS:
    1. The Executive Summary must be a high-level narrative for stakeholders.
    2. The Remediation Plan must contain CONCRETE, FILE-LEVEL steps (Actionable Items).
    3. Refer to specific file paths from the Verified Files list if applicable.
    
    Deterministic Stats:
    {executive_summary}
    
    Verified Files: {", ".join(verified_paths[:20])} 
    
    Detailed Remediation Context:
    {detailed_remediation_context}
    """

    for model in justice_llms:
        time.sleep(1.0)
        model_name = getattr(model, "model_name", getattr(model, "model", "Unknown"))
        try:
            structured_llm = model.with_structured_output(JusticeOutput)
            if not structured_llm:
                continue
                
            resp = structured_llm.invoke([
                SystemMessage(content="You are the Chief Justice. Produce a structured audit report with executive summary and concrete file-level remediation steps."),
                HumanMessage(content=prompt)
            ])
            
            if resp:
                executive_summary_final = resp.summary
                remediation_plan_final = resp.remediation
                break
        except Exception as e:
            print(f"  [Justice] {model_name} failed: {str(e)[:100]}")
            continue

    final_report = AuditReport(
        repo_url=state["repo_url"],
        repo_name=(state["repo_url"].split("/")[-1] if state.get("repo_url") else None),
        overall_score=overall_score,
        executive_summary=executive_summary_final,
        criteria=results,
        remediation_plan=remediation_plan_final,
        verified_paths=verified_paths,
        hallucinated_paths=hallucinated_paths,
    )

    return {"final_report": final_report}
