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

class SelectedVideo(BaseModel):
    video_id: str
    title: str
    url: str
    duration_seconds: int = Field(ge=0)
    order: int = Field(ge=1)
    curriculum_role: str
    added_topics: list[str] = Field(default_factory=list)
    inclusion_reason: str
    evidence_source: Literal["transcript", "metadata"]
    confidence: float = Field(ge=0.0, le=1.0)

class RejectedVideo(BaseModel):
    video_id: str
    title: str
    rejection_category: Literal[
        "over_budget",
        "low_relevance",
        "learner_mismatch",
        "constraint_violation",
        "redundant",
        "insufficient_evidence",
        "better_alternative",
    ]
    rejection_reason: str

class Curriculum(BaseModel):
    persona_id: str
    title: str
    selected_videos: list[SelectedVideo] = Field(min_length=1)
    rejected_videos: list[RejectedVideo] = Field(default_factory=list)
    covered_topics: list[str] = Field(default_factory=list)
    uncovered_topics: list[str] = Field(default_factory=list)
    total_duration_seconds: int = Field(ge=0)
    budget_seconds: int = Field(gt=0)
    remaining_budget_seconds: int = Field(ge=0)
    limitations: list[str] = Field(default_factory=list)
class SelectedVideoDraft(BaseModel):
    candidate_number: int = Field(ge=1)
    order: int = Field(ge=1)
    curriculum_role: str
    added_topics: list[str] = Field(default_factory=list)
    inclusion_reason: str


class RejectedVideoDraft(BaseModel):
    candidate_number: int = Field(ge=1)
    rejection_category: Literal[
        "low_relevance",
        "learner_mismatch",
        "constraint_violation",
        "redundant",
        "insufficient_evidence",
        "better_alternative",
    ]
    rejection_reason: str


class CurriculumDraft(BaseModel):
    title: str
    selected_videos: list[SelectedVideoDraft] = Field(min_length=1)
    rejected_videos: list[RejectedVideoDraft] = Field(default_factory=list)
    covered_topics: list[str] = Field(default_factory=list)
    uncovered_topics: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

class EvaluationCheck(BaseModel):
    name: str
    passed: bool
    severity: Literal["error", "warning", "info"]
    detail: str


class DeterministicEvaluation(BaseModel):
    persona_id: str
    overall_passed: bool
    checks: list[EvaluationCheck] = Field(min_length=1)
    metrics: dict[str, float | int] = Field(default_factory=dict)