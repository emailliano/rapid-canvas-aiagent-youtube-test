import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from src.models import (
    CandidateAssessment,
    CandidateAssessmentBatch,
    CandidateAssessmentDraftBatch,
    CurriculumDraft,
    LearningRequest,
    SearchPlan,
    VideoCandidate,
    VideoEvidence,
)

load_dotenv()


def create_search_plan(request: LearningRequest) -> SearchPlan:
    """Translate a learner's needs into a focused video-search strategy."""

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

    instructions = """
You are planning YouTube discovery for a personalized learning curriculum.

Determine:
1. The topics the learner must cover to achieve the goal.
2. Topics or content styles that should be excluded because they are already
   known, irrelevant, too superficial, or explicitly unwanted.
3. Between 3 and 6 complementary YouTube search queries.

The queries should collectively discover:
- necessary setup or prerequisites,
- practical instruction for the central skills,
- project-based content aligned with the learner's goal.

Do not search for topics the learner already knows unless they are inseparable
from the requested project. Make queries specific enough to reduce irrelevant
results.
""".strip()

    response = client.responses.parse(
        model=model,
        instructions=instructions,
        input=request.model_dump_json(indent=2),
        text_format=SearchPlan,
    )

    if response.output_parsed is None:
        raise RuntimeError("The model did not return a valid search plan.")

    return response.output_parsed


def assess_candidates(
    request: LearningRequest,
    plan: SearchPlan,
    candidates: list[VideoCandidate],
    evidence: list[VideoEvidence],
) -> CandidateAssessmentBatch:
    """Assess candidate videos against the learner, goal, and evidence."""

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

    evidence_by_id = {
        item.video_id: item
        for item in evidence
    }

    candidate_payload = []

    for candidate_number, candidate in enumerate(candidates, start=1):
        candidate_evidence = evidence_by_id.get(candidate.video_id)

        if candidate_evidence is None:
            raise ValueError(
                f"Missing evidence for video {candidate.video_id}"
            )

        candidate_payload.append(
            {
                "candidate_number": candidate_number,
                "video": candidate.model_dump(
                    exclude={"discovery_query", "video_id"}
                ),
                "evidence": candidate_evidence.model_dump(
                    exclude={"video_id"}
                ),
            }
        )

    payload = {
        "learner_request": request.model_dump(),
        "search_plan": plan.model_dump(),
        "candidates": candidate_payload,
    }

    instructions = """
You are evaluating YouTube candidates for a personalized learning curriculum.

Assess every candidate exactly once.
Return the supplied candidate_number exactly as an integer for each assessment.
Do not invent candidate labels or identifiers.

For each candidate:
- Score relevance to the concrete learning goal from 0 to 10.
- Score fit for the learner's background and knowledge gaps from 0 to 10.
- Score compliance with the learner's preferences and constraints from 0 to 10.
- Identify the required topics it appears to cover.
- Give a concise inclusion reason grounded only in the provided evidence.
- List concerns such as excessive length, likely repetition, irrelevant technology,
  beginner material the learner already knows, or superficial coverage.
- Preserve the supplied evidence source exactly.
- Assign confidence according to evidence quality and ambiguity.

Important evidence rules:
- You must return one assessment for every supplied candidate, even when the
  candidate is irrelevant, ambiguous, or supported only by metadata.
- Insufficient evidence must lower confidence and appear as a concern; it must
  never cause you to omit a candidate or return an empty assessment list.
- When only metadata is available, make a cautious provisional assessment using
  only the title, channel, and duration.
- Do not claim topics, timestamps, teaching methods, or project steps that are
  not supported by the supplied evidence.
- Metadata-only reasons must use cautious language such as "the title indicates"
  or "the metadata suggests."
- Confidence for metadata-only evidence must not exceed 0.55.
- Confidence for transcript evidence must not exceed 0.95.
- A relevant title is not proof that the full video is suitable.
- Search queries and discovery provenance are not content evidence.
- Do not infer video coverage from the terms used to discover a candidate.
- Low-quality or irrelevant candidates should receive low scores rather than
  being omitted.
- Do not select a final curriculum yet. Only assess candidates independently.
""".strip()
    print(
        f"Sending {len(candidate_payload)} candidates "
        "to the assessment model."
    )
    response = client.responses.parse(
        model=model,
        instructions=instructions,
        input=json.dumps(payload, indent=2),
        text_format=CandidateAssessmentDraftBatch,
    )

    draft_batch = response.output_parsed

    if draft_batch is None:
        raise RuntimeError(
            "The model did not return valid candidate assessments."
        )

    expected_numbers = set(
        range(1, len(candidates) + 1)
    )
    returned_numbers = {
        assessment.candidate_number
        for assessment in draft_batch.assessments
    }

    if returned_numbers != expected_numbers:
        missing = expected_numbers - returned_numbers
        unexpected = returned_numbers - expected_numbers

        raise RuntimeError(
            "Candidate assessment number mismatch. "
            f"Missing: {sorted(missing)}. "
            f"Unexpected: {sorted(unexpected)}."
        )

    if len(draft_batch.assessments) != len(candidates):
        raise RuntimeError(
            "The model returned duplicate candidate assessments."
        )

    converted_assessments = []

    for draft in draft_batch.assessments:
        candidate = candidates[draft.candidate_number - 1]

        converted_assessments.append(
            CandidateAssessment(
                video_id=candidate.video_id,
                **draft.model_dump(
                    exclude={"candidate_number"}
                ),
            )
        )

    assessments = CandidateAssessmentBatch(
        assessments=converted_assessments
    )

    for assessment in assessments.assessments:
        original_evidence = evidence_by_id[assessment.video_id]

        if assessment.evidence_source != original_evidence.evidence_source:
            raise RuntimeError(
                f"Evidence source mismatch for video {assessment.video_id}: "
                f"expected {original_evidence.evidence_source}, "
                f"received {assessment.evidence_source}."
            )

        if (
            assessment.evidence_source == "metadata"
            and assessment.confidence > 0.55
        ):
            raise RuntimeError(
                f"Metadata confidence too high for video "
                f"{assessment.video_id}: {assessment.confidence}"
            )

        if (
            assessment.evidence_source == "transcript"
            and assessment.confidence > 0.95
        ):
            raise RuntimeError(
                f"Transcript confidence too high for video "
                f"{assessment.video_id}: {assessment.confidence}"
            )

    return assessments


def assess_candidates_in_batches(
    request: LearningRequest,
    plan: SearchPlan,
    candidates: list[VideoCandidate],
    evidence: list[VideoEvidence],
    batch_size: int = 6,
) -> CandidateAssessmentBatch:
    """Assess a large candidate pool through smaller validated API calls."""

    if not candidates:
        raise ValueError("Cannot assess an empty candidate list.")

    if batch_size <= 0:
        raise ValueError("Batch size must be greater than zero.")

    evidence_by_id = {
        item.video_id: item
        for item in evidence
    }

    all_assessments = []

    for start in range(0, len(candidates), batch_size):
        candidate_batch = candidates[start:start + batch_size]

        evidence_batch = [
            evidence_by_id[candidate.video_id]
            for candidate in candidate_batch
        ]

        result = assess_candidates(
            request=request,
            plan=plan,
            candidates=candidate_batch,
            evidence=evidence_batch,
        )

        all_assessments.extend(result.assessments)

    return CandidateAssessmentBatch(
        assessments=all_assessments
    )
def create_curriculum_draft(
    request: LearningRequest,
    plan: SearchPlan,
    candidates: list[VideoCandidate],
    assessments: CandidateAssessmentBatch,
) -> CurriculumDraft:
    """Select and order a complementary curriculum from assessed candidates."""

    if not candidates:
        raise ValueError(
            "Cannot create a curriculum from an empty candidate list."
        )

    assessment_by_id = {
        assessment.video_id: assessment
        for assessment in assessments.assessments
    }

    candidate_ids = {
        candidate.video_id
        for candidate in candidates
    }
    assessment_ids = set(assessment_by_id)

    if assessment_ids != candidate_ids:
        raise ValueError(
            "Candidate and assessment IDs do not match."
        )

    numbered_candidates = []

    for candidate_number, candidate in enumerate(candidates, start=1):
        assessment = assessment_by_id[candidate.video_id]

        numbered_candidates.append(
            {
                "candidate_number": candidate_number,
                "video": candidate.model_dump(
                    exclude={"video_id", "discovery_query"}
                ),
                "assessment": assessment.model_dump(
                    exclude={"video_id"}
                ),
            }
        )

    payload = {
        "learner_request": request.model_dump(),
        "search_plan": plan.model_dump(),
        "candidates": numbered_candidates,
    }

    instructions = """
You are constructing a personalized YouTube learning curriculum from an
already-assessed candidate pool.

Select a complementary subset and arrange it in pedagogical order.

Selection principles:
- Prefer 4 to 6 videos when the candidate pool and time budget justify it.
- A smaller curriculum is acceptable when additional videos would be redundant,
  poorly supported, or unnecessary.
- Do not select by average score alone.
- Consider relevance, learner fit, constraint fit, duration, evidence quality,
  required-topic coverage, sequencing, and marginal contribution.
- Avoid selecting two videos that appear to teach substantially the same material
  unless the second provides necessary reinforcement or distinct depth.
- Prefer one strong project spine plus only the foundation or gap-filling videos
  needed around it.
- Do not exceed the learner's time budget.
- Do not add a weak video merely to consume unused time.
- Use only supplied candidates.
- Use candidate_number exactly as provided.

Reasoning requirements:
- curriculum_role should describe the video's pedagogical purpose.
- added_topics should identify its incremental contribution relative to earlier
  selected videos, not every topic it might cover.
- inclusion reasons must remain grounded in the supplied evidence.
- Treat metadata-based coverage as provisional.
- Every unselected eligible candidate must appear once in rejected_videos.
- Explicitly identify required topics that remain uncovered or unverified.
""".strip()

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

    response = client.responses.parse(
        model=model,
        instructions=instructions,
        input=json.dumps(payload, indent=2),
        text_format=CurriculumDraft,
    )

    draft = response.output_parsed

    if draft is None:
        raise RuntimeError(
            "The model did not return a valid curriculum draft."
        )

    selected_numbers = [
        item.candidate_number
        for item in draft.selected_videos
    ]
    rejected_numbers = [
        item.candidate_number
        for item in draft.rejected_videos
    ]
    expected_numbers = set(
        range(1, len(candidates) + 1)
    )

    if len(selected_numbers) != len(set(selected_numbers)):
        raise RuntimeError(
            "The curriculum selected a candidate more than once."
        )

    if len(rejected_numbers) != len(set(rejected_numbers)):
        raise RuntimeError(
            "The curriculum rejected a candidate more than once."
        )

    if set(selected_numbers) & set(rejected_numbers):
        raise RuntimeError(
            "A candidate cannot be both selected and rejected."
        )

    returned_numbers = set(selected_numbers) | set(rejected_numbers)

    if returned_numbers != expected_numbers:
        missing = expected_numbers - returned_numbers
        unexpected = returned_numbers - expected_numbers

        raise RuntimeError(
            "Curriculum candidate-number mismatch. "
            f"Missing: {sorted(missing)}. "
            f"Unexpected: {sorted(unexpected)}."
        )

    orders = [
        item.order
        for item in draft.selected_videos
    ]
    expected_orders = list(
        range(1, len(draft.selected_videos) + 1)
    )

    if sorted(orders) != expected_orders:
        raise RuntimeError(
            "Selected-video order must be consecutive starting at 1."
        )

    selected_duration = sum(
        candidates[number - 1].duration_seconds or 0
        for number in selected_numbers
    )
    budget_seconds = request.time_budget_minutes * 60

    if selected_duration > budget_seconds:
        raise RuntimeError(
            f"Curriculum exceeds budget: {selected_duration} seconds "
            f"selected for a {budget_seconds}-second budget."
        )

    return draft