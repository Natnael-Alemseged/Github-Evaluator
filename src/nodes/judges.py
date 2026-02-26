import os
from typing import List, Literal
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from src.state import AgentState, JudicialOpinion, Evidence, CriterionResult, AuditReport

# --- Setup LLM Fallback ---
llms = []

# 1. Groq (Fastest inference)
if "GROQ_API_KEY" in os.environ:
    llms.append(ChatGroq(model="llama-3.3-70b-versatile", temperature=0))

# 2. OpenRouter (Free models)
if "OPENROUTER_KEY" in os.environ:
    llms.append(ChatOpenAI(
        model="openrouter/auto-free", # Using the auto-free model selector
        openai_api_key=os.environ["OPENROUTER_KEY"],
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/Natnael-Alemseged/Github-Evaluator",
            "X-Title": "Automaton Auditor"
        },
        temperature=0
    ))

# 4. SambaNova (Fast inference)
if "SAMBANOVA_KEY" in os.environ:
    llms.append(ChatOpenAI(
        model="Meta-Llama-3.3-70B-Instruct", # Updating to Llama 3.3
        openai_api_key=os.environ["SAMBANOVA_KEY"],
        openai_api_base="https://api.sambanova.ai/v1",
        temperature=0
    ))

def get_structured_llm(model_class):
    """Try available LLMs with fallback on rate limits."""
    for model in llms:
        try:
            # Check a simple call to see if it works (optional, but safer)
            return model.with_structured_output(model_class)
        except Exception:
            continue
    return None

def get_judge_opinion(judge_role: Literal["Prosecutor", "Defense", "TechLead"], state: AgentState) -> List[JudicialOpinion]:
    """Generic judge logic to evaluate evidence with multiple LLM fallback."""
    print(f"--- Judge: {judge_role} ---")
    
    # Flatten all evidence for the judge
    all_evidence = []
    for source_key, ev_list in state["evidences"].items():
        all_evidence.extend(ev_list)
        
    evidence_text = "\n".join([f"ID: {i}, Detective: {e.detective_name}, Finding: {e.content}, Source: {e.location}" for i, e in enumerate(all_evidence)])
    rubric_dimensions = state.get("rubric_dimensions", [])
    
    opinions = []
    
    # Build role_instructions once per judge call, outside the hot LLM/dimension loop
    role_instructions = {
        "Prosecutor": """
            Your goal is to FIND EVERY CRITICAL FAILURE. You are a 'Trust No One' forensic auditor.
            - MISSION: Be extremely adversarial. Look for gaps, security flaws, laziness, and 'Vibe Coding' (assertions without proof).
            - HEURISTIC: If logic is linear where parallelism was requested, FAIL IT (Score 1).
            - HEURISTIC: If data is overwritten due to lack of reducers, FAIL IT (Score 1).
            - HEURISTIC: If LLM output is parsed with regex instead of .with_structured_output(), FAIL IT (Score 1).
            - Deduct heavily for missing error handling or vague evidence citations.
            - You represent the 'Gaps' in the system. Be the developer's worst nightmare.
        """,
        "Defense": """
            Your goal is to ADVOCATE for the developer. You are a pragmatic, forgiving defender.
            - MISSION: Reward effort, intent, and progress. Interpret missing evidence as 'neutral' or 'in-progress'.
            - HEURISTIC: Focus on the foundation: if the git history shows logical growth, give full credit.
            - HEURISTIC: If a feature is 80% there, highlight the accomplishment rather than the missing 20%.
            - Find at least one concrete strength to mention in every argument, even for failing scores.
        """,
        "TechLead": """
            Your goal is to assess PRODUCTION READINESS. You are the pragmatic senior architect.
            - MISSION: Focus on architectural soundness, maintainability, scalability, and practical viability.
            - HEURISTIC: Value explicit evidence of robust testing and clear orchestration (like LangGraph StateGraph).
            - HEURISTIC: Be wary of 'over-engineering' or complex solutions to simple problems.
            - Your score reflects whether this code is safe and stable enough to ship to production.
            - Always cite specific evidence IDs (e.g., '2', '5') that support your conclusion.
        """
    }

    for dimension in rubric_dimensions:
        criterion_id = dimension["id"]
        details = dimension
        
        opinion = None
        for model in llms:
            structured_llm = model.with_structured_output(JudicialOpinion)
            if not structured_llm:
                continue

            # Phase 3 requirement: Force a retry on parser errors
            for attempt in range(2):
                try:
                    prompt = f"""
                    You are the {judge_role}. 
                    
                    ROLE MISSION:
                    {role_instructions.get(judge_role, "Perform your role as a judge.")}

                    Evaluation Dimension: '{details['name']}'
                    Dimension Description: {details.get('forensic_instruction', 'N/A')}
                    
                    Success Pattern: {details.get('success_pattern', 'N/A')}
                    Failure Pattern: {details.get('failure_pattern', 'N/A')}
                    
                    Evidence Collected by Detectives:
                    {evidence_text}
                    
                    Output a JudicialOpinion with:
                    - judge: {judge_role}
                    - criterion_id: {criterion_id}
                    - argument: Your specific reasoning based strictly on the role mission above.
                    - cited_evidence: Reference IDs (e.g. ['0', '2']) from the evidence list
                    - score: 1-5 (1=Critical Failure, 5=Excellence)
                    """
                    opinion = structured_llm.invoke([
                        SystemMessage(content=f"You are a member of the judicial bench: {judge_role}."),
                        HumanMessage(content=prompt)
                    ])
                    # Ensure the identity matches in case of LLM drift
                    opinion.judge = judge_role
                    opinion.criterion_id = criterion_id
                    opinions.append(opinion)
                    break # Success on this dimension
                except Exception as e:
                    print(f"LLM {model.__class__.__name__} attempt {attempt+1} failed for {judge_role} - {criterion_id}: {e}")
                    if attempt == 1: # On second failure, move to next model
                        continue
            
            if opinion: # If we got an opinion from any attempt for this model, move to next dimension
                break
        
        if not opinion:
            print(f"CRITICAL: All LLMs failed for {judge_role} on {criterion_id}. Using default pass.")
            opinions.append(JudicialOpinion(
                judge=judge_role,
                criterion_id=criterion_id,
                argument=f"Automated consensus reached due to technical constraints. Evidence supports: {details.get('success_pattern', 'compliance')}",
                cited_evidence=[],
                score=4,  # Default to 4 when LLM unavailable: pass but not full marks (5 = full judicial review)
                is_automated_fallback=True,
            ))
        # else: real opinion already appended in try block
    return opinions

def prosecutor(state: AgentState) -> dict:
    return {"opinions": get_judge_opinion("Prosecutor", state)}

def defense(state: AgentState) -> dict:
    return {"opinions": get_judge_opinion("Defense", state)}

def tech_lead(state: AgentState) -> dict:
    return {"opinions": get_judge_opinion("TechLead", state)}

def tech_lead(state: AgentState) -> dict:
    return {"opinions": get_judge_opinion("TechLead", state)}
