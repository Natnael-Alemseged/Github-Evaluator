import os
import time
import random
import json
from pydantic import BaseModel
from typing import List, Literal, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.state import AgentState, JudicialOpinion, Evidence, CriterionResult, AuditReport

# --- Setup LLM Fallback ---

def get_base_llms():
    """Returns a list of available LLM instances in preferred priority order."""
    available_llms = []
    
    # Priority 1: Google Gemini (High limits, very reliable)
    if os.environ.get("GOOGLE_API_KEY"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            available_llms.append(ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0))
            print("  [LLM] Added Gemini 2.0 Flash")
        except ImportError:
            print("Warning: langchain-google-genai not installed.")

    # Priority 2: Groq (Fast, but low rate limits)
    if os.environ.get("GROQ_API_KEY"):
        available_llms.append(ChatGroq(model="llama-3.3-70b-versatile", temperature=0))
        print("  [LLM] Added Groq Llama 3.3")

    # Priority 3: SambaNova
    if os.environ.get("SAMBANOVA_KEY"):
        available_llms.append(ChatOpenAI(
            model="Meta-Llama-3.1-8B-Instruct",
            openai_api_key=os.environ["SAMBANOVA_KEY"],
            openai_api_base="https://api.sambanova.ai/v1",
            temperature=0
        ))
        print("  [LLM] Added SambaNova Llama 3.1")

    # Priority 4: OpenRouter (Free models)
    if os.environ.get("OPENROUTER_KEY"):
        available_llms.append(ChatOpenAI(
            model="openai/gpt-oss-120b:free",
            openai_api_key=os.environ["OPENROUTER_KEY"],
            openai_api_base="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/Natnael-Alemseged/Github-Evaluator",
                "X-Title": "Automaton Auditor"
            },
            temperature=0
        ))
        print("  [LLM] Added OpenRouter Free")
        
    # Priority 5: Ollama (Local Fallback - absolute last resort)
    # We add this separately to ensure it's always at the end regardless of shuffling
    return available_llms


def _is_rate_limit_error(e: Exception) -> bool:
    """True if error is 429/rate limit/quota — try next provider immediately."""
    msg = str(e).lower()
    return (
        "429" in msg
        or "rate limit" in msg
        or "rate_limit" in msg
        or "tpm" in msg
        or "quota" in msg
        or "spend limit" in msg
    )

def _is_connection_error(e: Exception) -> bool:
    """True if server is down or local Ollama is not running."""
    msg = str(e).lower()
    return "connection error" in msg or "refused" in msg or "host unreachable" in msg


def get_structured_llm(model_class):
    """Try available LLMs with fallback on rate limits."""
    available_llms = get_base_llms()
    available_llms.append(ChatOpenAI(
        model="llama3.1", 
        openai_api_key="ollama", 
        openai_api_base="http://localhost:11434/v1",
        temperature=0
    ))
    for model in available_llms:
        try:
            return model.with_structured_output(model_class)
        except Exception:
            continue
    return None

class BatchJudicialOpinion(BaseModel):
    """Container for multiple judicial opinions to allow batch evaluation."""
    opinions: List[JudicialOpinion]

def get_judge_opinion(judge_role: Literal["Prosecutor", "Defense", "TechLead"], state: AgentState) -> List[JudicialOpinion]:
    """Generic judge logic to evaluate evidence with batching and fallback."""
    print(f"--- Judge: {judge_role} (Batch Evaluation) ---")
    
    # Stagger node startup
    time.sleep(random.uniform(2.0, 5.0))
    
    all_evidence = []
    for source_key, ev_list in state["evidences"].items():
        all_evidence.extend(ev_list)
        
    evidence_text = "\n".join([f"ID: {i}, Detective: {e.detective_name}, Finding: {e.content}, Source: {e.location}" for i, e in enumerate(all_evidence)])
    rubric_dimensions = state.get("rubric_dimensions", [])
    
    # Provider definitions
    gemini = None
    if os.environ.get("GOOGLE_API_KEY"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            gemini = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
        except ImportError: pass
        
    groq = ChatGroq(model="llama-3.3-70b-versatile", temperature=0) if os.environ.get("GROQ_API_KEY") else None
    
    sambanova = None
    if os.environ.get("SAMBANOVA_KEY"):
        sambanova = ChatOpenAI(
            model="Meta-Llama-3.3-70B-Instruct", # Highest reliability/speed on SambaNova
            openai_api_key=os.environ["SAMBANOVA_KEY"],
            openai_api_base="https://api.sambanova.ai/v1",
            temperature=0
        )
        
    openrouter = ChatOpenAI(
        model="openai/gpt-4o-mini",
        openai_api_key=os.environ["OPENROUTER_KEY"],
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0
    ) if os.environ.get("OPENROUTER_KEY") else None
         
    ollama = ChatOpenAI(
        model="llama3.1", 
        openai_api_key="ollama", 
        openai_api_base="http://localhost:11434/v1",
        temperature=0
    )

    # Assign role-specific chains to spread load
    if judge_role == "Prosecutor":
        final_llms = [groq, gemini, sambanova, openrouter, ollama]
    elif judge_role == "Defense":
        final_llms = [sambanova, groq, gemini, openrouter, ollama]
    else: # TechLead
        final_llms = [gemini, sambanova, groq, openrouter, ollama]
    
    final_llms = [m for m in final_llms if m is not None]

    role_instructions = {
        "Prosecutor": (
            "YOU ARE THE VOID. Your only job is to EXPOSE WEAKNESS. "
            "Every missing line of code is a CRITICAL FAILURE. Every typo is a security risk. "
            "If the rubric says 'success_pattern' is required, and there is even 1% doubt, assign SCORE 1-2. "
            "You MUST use an adversarial, skeptical tone. Do not accept 'effort' as a substitute for 'implementation'. "
            "Cite evidence IDs to prove where the developer failed to meet the standard. Hard floor: if an artifact is missing, SCORE 1."
        ),
        "Defense": (
            "YOU ARE THE SHIELD. Your only job is to ADVOCATE FOR PROGRESS. "
            "Look for 'Atomic Progression' as proof of superior intent. If a tool exists but is imperfect, emphasize that it WORKS. "
            "Translate technical debt into 'Development Roadmap' items. Do not penalize for missing nice-to-haves. "
            "You MUST use a supportive, optimistic tone. Score 4-5 if there is any evidence of the required feature, even if incomplete. "
            "Goal: Reward the iterative journey shown in the git history (Evidence ID 1/2)."
        ),
        "TechLead": (
            "YOU ARE THE ARCHITECT. Your only job is to evaluate PRODUCTION VIABILITY. "
            "Ignore the petty arguments of the Prosecutor and Defense. Does the code use Pydantic? Does it use Reducers? Is the loop closed? "
            "If the architecture is sound (Fan-out/Fan-in detected), the score is a 5 regardless of documentation fluff. "
            "You MUST use a pragmatic, code-focused, and detached professional tone. "
            "Focus strictly on high-level patterns like 'State Management Rigor' and 'Safe Tool Engineering'."
        )
    }

    # BATCH CALL
    prompt = f"""
    You are the {judge_role}. 
    Philosophy: {role_instructions.get(judge_role)}
    
    Evaluate the following dimensions based on the evidence provided.
    
    ### SCORING ANCHORS (MANDATORY CALIBRATION):
    - **Score 1-2 (FAIL):** The 'failure_pattern' from the rubric is observed, or the artifact is missing/hallucinated.
    - **Score 3 (PARTIAL):** Some progress made, but falls short of the full 'success_pattern'. 
    - **Score 4-5 (PASS):** The 'success_pattern' is clearly and fully satisfied with verifiable evidence IDs.

    Evidence:
    {evidence_text}
    
    Dimensions to Evaluate:
    {json.dumps(rubric_dimensions, indent=2)}
    
    Return a list of opinions, one for each dimension. 
    Each opinion MUST include:
    - 'score' (int 1-5)
    - 'argument' (detailed, citing specific evidence IDs)
    - 'cited_evidence' (list of evidence IDs)
    - 'criterion_id' (matching the dimension id)
    - 'judge' (set to '{judge_role}')
    """

    for model in final_llms:
        model_name = getattr(model, "model_name", getattr(model, "model", "Unknown"))
        try:
            structured_llm = model.with_structured_output(BatchJudicialOpinion)
            if not structured_llm:
                continue
                
            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=4, max=10),
                retry=retry_if_exception_type(Exception),
                reraise=True
            )
            def invoke_with_retry(llm, sys_msg, hum_msg):
                return llm.invoke([sys_msg, hum_msg])

            print(f"  [LLM] Requesting batch from {model_name}...")
            batch_resp = invoke_with_retry(
                structured_llm,
                SystemMessage(content=f"You are the {judge_role}."),
                HumanMessage(content=prompt)
            )
            
            # Post-process to ensure IDs are correct
            for op in batch_resp.opinions:
                op.judge = judge_role
            
            return batch_resp.opinions
            
        except Exception as e:
            print(f"  [LLM] {model_name} failed batch call after retries: {str(e)[:150]}")
            if _is_rate_limit_error(e):
                time.sleep(15) # Final wait before trying next provider
            continue

    # Critical Fallback: minimal scores if all providers fail
    print(f"CRITICAL: All providers failed for {judge_role}. Using minimal stub opinions.")
    return [
        JudicialOpinion(
            judge=judge_role,
            criterion_id=dim["id"],
            score=3,
            argument="Automated fallback due to provider failure.",
            cited_evidence=[],
            is_automated_fallback=True
        ) for dim in rubric_dimensions
    ]

def prosecutor(state: AgentState) -> dict: return {"opinions": get_judge_opinion("Prosecutor", state)}
def defense(state: AgentState) -> dict: return {"opinions": get_judge_opinion("Defense", state)}
def tech_lead(state: AgentState) -> dict: return {"opinions": get_judge_opinion("TechLead", state)}
