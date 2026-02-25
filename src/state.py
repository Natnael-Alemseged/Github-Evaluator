import operator
from typing import Annotated, TypedDict, List, Literal, Optional
from pydantic import BaseModel, Field

# --- Pydantic Models for Structured Output ---

class Evidence(BaseModel):
    """Objective finding from a detective, with no judgments."""
    detective_name: str = Field(description="Name of the detective (e.g., RepoInvestigator)")
    goal: str = Field(description="What the detective was looking for")
    found: bool = Field(description="Whether the target of the investigation was found")
    content: Optional[str] = Field(None, description="The actual content or data discovered")
    location: str = Field(description="Where this was found (file path, line number, doc section)")
    rationale: str = Field(description="Why this is relevant to the objective")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")

class JudicialOpinion(BaseModel):
    """Evaluation of evidence against a specific criterion."""
    judge: Literal["Prosecutor", "Defense", "TechLead"] = Field(description="Identity of the judge")
    criterion_id: str = Field(description="The ID of the criterion being evaluated")
    argument: str = Field(description="Detailed reasoning based strictly on cited evidence")
    cited_evidence: List[str] = Field(description="List of evidence IDs or findings used in the argument")
    score: int = Field(ge=1, le=5, description="Score 1-5")
    is_automated_fallback: bool = Field(default=False, description="True when LLM failed and a stub opinion was used")

class CriterionResult(BaseModel):
    """Final determination for a single grading rubric line item."""
    dimension_id: str = Field(description="ID of the rubric dimension")
    dimension_name: str = Field(description="Name of the rubric dimension")
    final_score: float = Field(description="Aggregated final score")
    verdict: str = Field(description="Pass/Fail or qualitative result")
    judge_opinions: List[JudicialOpinion] = Field(description="Opinions that led to this result")
    dissent_summary: Optional[str] = Field(description="Summary of any major disagreements between judges")
    remediation: str = Field(description="Suggested fix for failures")

class AuditReport(BaseModel):
    """The final compiled report."""
    repo_url: str = Field(description="URL of the audited repository")
    repo_name: str = Field(description="Name of the repository")
    overall_score: float = Field(description="Total weighted score")
    executive_summary: str = Field(description="High-level summary for stakeholders")
    criteria: List[CriterionResult] = Field(description="List of detailed dimension results")
    remediation_plan: str = Field(description="Prioritized list of steps to improve the score")
    verified_paths: List[str] = Field(default_factory=list, description="Paths verified to exist in the repository")
    hallucinated_paths: List[str] = Field(default_factory=list, description="Paths hallucinated by LLMs or detectives")

# --- AgentState (TypedDict) ---

class AgentState(TypedDict):
    """State graph for the LangGraph agents."""
    repo_url: str
    repo_path: Optional[str]
    rubric: dict
    
    # Reducers for parallel branch state merging
    # operator.ior merges dictionaries
    evidences: Annotated[dict[str, List[Evidence]], operator.ior]
    
    # operator.add concatenates lists
    opinions: Annotated[List[JudicialOpinion], operator.add]
    
    verified_paths: Annotated[List[str], operator.add]
    hallucinated_paths: Annotated[List[str], operator.add]
    repo_manifest: List[str]
    
    # The final output
    final_report: Optional[AuditReport]
