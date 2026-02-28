import operator
from typing import Annotated, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

# --- Detective Output ---

class Evidence(BaseModel):
    """Objective finding from a detective, with no judgments."""
    detective_name: str = Field(description="Name of the detective (e.g., RepoInvestigator)")
    goal: str = Field()
    found: bool = Field(description="Whether the target of the investigation was found")
    content: Optional[str] = Field(default=None, description="The actual content or data discovered")
    location: str = Field(description="Where this was found (file path, line number, doc section)")
    rationale: str = Field(description="Your rationale for your confidence on the evidence you find for this particular goal")
    confidence: float

# --- Judge Output ---

class JudicialOpinion(BaseModel):
    """Evaluation of evidence against a specific criterion."""
    judge: Optional[Literal["Prosecutor", "Defense", "TechLead"]] = None
    criterion_id: Optional[str] = None
    score: int = Field(ge=1, le=5, description="Score 1-5")
    argument: str = Field(description="Detailed reasoning based strictly on cited evidence")
    cited_evidence: List[str] = Field(description="List of evidence IDs or findings used in the argument")
    is_automated_fallback: bool = Field(default=False, description="True when LLM failed and a stub opinion was used")

# --- Chief Justice Output ---

class CriterionResult(BaseModel):
    """Final determination for a single grading rubric line item."""
    dimension_id: str
    dimension_name: str
    final_score: int = Field(ge=1, le=5)
    judge_opinions: List[JudicialOpinion]
    dissent_summary: Optional[str] = Field(
        default=None,
        description="Required when score variance > 2",
    )
    remediation: str = Field(
        description="Specific file-level instructions for improvement",
    )

class JusticeOutput(BaseModel):
    """Structured output for the Chief Justice synthesis."""
    summary: str = Field(description="The polished executive summary narrative")
    remediation: str = Field(description="The polished remediation plan narrative")

class AuditReport(BaseModel):
    """The final compiled report."""
    repo_url: str
    executive_summary: str
    overall_score: float
    criteria: List[CriterionResult]
    remediation_plan: str
    # Extensions to satisfy existing logic
    repo_name: Optional[str] = None
    verified_paths: List[str] = Field(default_factory=list)
    hallucinated_paths: List[str] = Field(default_factory=list)

# --- Graph State ---

class AgentState(TypedDict):
    """State graph for the LangGraph agents."""
    repo_url: str
    pdf_path: str
    rubric_dimensions: List[Dict]
    
    # Use reducers to prevent parallel agents from overwriting data
    evidences: Annotated[Dict[str, List[Evidence]], operator.ior]
    opinions: Annotated[List[JudicialOpinion], operator.add]
    
    # Keep extensions for existing logic
    repo_path: Optional[str]
    verified_paths: Annotated[List[str], operator.add]
    hallucinated_paths: Annotated[List[str], operator.add]
    repo_manifest: List[str]
    
    final_report: Optional[AuditReport]
