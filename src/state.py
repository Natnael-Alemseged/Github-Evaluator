import operator
from typing import Annotated, TypedDict, List
from pydantic import BaseModel, Field

# --- Pydantic Models for Structured Output ---

class Evidence(BaseModel):
    """Objective finding from a detective, with no judgments."""
    detective_name: str = Field(description="Name of the detective (e.g., RepoInvestigator)")
    finding: str = Field(description="The objective fact or evidence discovered")
    source: str = Field(description="Where this was found (file path, line number, doc section)")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")

class JudicialOpinion(BaseModel):
    """Evaluation of evidence against a specific criterion."""
    criterion: str = Field(description="The criterion being evaluated")
    assessment: str = Field(description="Detailed reasoning based strictly on evidence")
    score: float = Field(description="Score out of 10")

class CriterionResult(BaseModel):
    """Final determination for a single grading rubric line item."""
    criterion_id: str = Field(description="ID of the rubric item")
    verdict: str = Field(description="Pass/Fail or qualitative result")
    justification: str = Field(description="Summary of the judicial opinions leading to this verdict")

class AuditReport(BaseModel):
    """The final compiled report."""
    target_repo: str = Field(description="URL of the audited repository")
    overall_summary: str = Field(description="High-level summary of the audit")
    results: List[CriterionResult] = Field(description="List of criterion results")

# --- AgentState (TypedDict) ---

class AgentState(TypedDict):
    """State graph for the LangGraph agents."""
    repo_url: str
    rubric: dict  # TODO: Load from rubric.json
    
    # Reducers for parallel branch state merging
    # operator.ior merges dictionaries
    evidences: Annotated[dict[str, List[Evidence]], operator.ior]
    
    # operator.add concatenates lists
    opinions: Annotated[List[JudicialOpinion], operator.add]
    
    # The final output
    final_report: AuditReport | None
