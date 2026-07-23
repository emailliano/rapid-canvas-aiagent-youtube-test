import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from src.models import (
    CandidateAssessment,
    CandidateAssessmentBatch,
    CandidateAssessmentDraftBatch,
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