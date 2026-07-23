from typing import Literal
from pydantic import BaseModel, Field


class UserContext(BaseModel):
    background: str
    known: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    constraints: str = ""


class LearningRequest(BaseModel):
    persona_id: str
    goal: str
    time_budget_minutes: int = Field(gt=0)
    user_context: UserContext

class VideoCandidate(BaseModel):
    video_id: str
    title: str
    url: str
    duration_seconds: int | None = Field(default=None, ge=0)
    channel: str | None = None
    discovery_query: str

class SearchPlan(BaseModel):
    required_topics: list[str] = Field(min_length=1)
    excluded_topics: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(min_length=3, max_length=6)
class CandidateAssessmentDraft(BaseModel):
    candidate_number: int = Field(ge=1)
    relevance_score: int = Field(ge=0, le=10)
    learner_fit_score: int = Field(ge=0, le=10)
    constraint_fit_score: int = Field(ge=0, le=10)
    covered_topics: list[str] = Field(default_factory=list)
    inclusion_reason: str
    concerns: list[str] = Field(default_factory=list)
    evidence_source: Literal["transcript", "metadata"]
    confidence: float = Field(ge=0.0, le=1.0)


class CandidateAssessmentDraftBatch(BaseModel):
    assessments: list[CandidateAssessmentDraft] = Field(min_length=1)
class CandidateAssessment(BaseModel):
    video_id: str
    relevance_score: int = Field(ge=0, le=10)
    learner_fit_score: int = Field(ge=0, le=10)
    constraint_fit_score: int = Field(ge=0, le=10)
    covered_topics: list[str] = Field(default_factory=list)
    inclusion_reason: str
    concerns: list[str] = Field(default_factory=list)
    evidence_source: Literal["transcript", "metadata"]
    confidence: float = Field(ge=0.0, le=1.0)

class CandidateAssessmentBatch(BaseModel):
    assessments: list[CandidateAssessment] = Field(min_length=1)
class VideoEvidence(BaseModel):
    video_id: str
    evidence_text: str
    evidence_source: Literal["transcript", "metadata"]
    retrieval_error: str | None = None