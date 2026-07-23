import json
from pathlib import Path

from src.agent import assess_candidates_in_batches
from src.models import (
    LearningRequest,
    SearchPlan,
    VideoCandidate,
    VideoEvidence,
)


def main() -> None:
    checkpoint_path = Path("tmp/assessment_context.json")

    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"Assessment checkpoint not found: {checkpoint_path}"
        )

    context = json.loads(
        checkpoint_path.read_text(encoding="utf-8")
    )

    request = LearningRequest.model_validate(
        context["request"]
    )
    plan = SearchPlan.model_validate(
        context["search_plan"]
    )
    candidates = [
        VideoCandidate.model_validate(item)
        for item in context["candidates"]
    ]
    evidence = [
        VideoEvidence.model_validate(item)
        for item in context["evidence"]
    ]

    print(
        f"Loaded checkpoint with {len(candidates)} candidates."
    )
    print("Skipping planning, YouTube search, and transcript retrieval.")
    print("Assessing saved candidates in batches of up to 5...")

    result = assess_candidates_in_batches(
        request=request,
        plan=plan,
        candidates=candidates,
        evidence=evidence,
        batch_size=5,
    )

    output_path = Path("tmp/assessment_result.json")
    output_path.write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )

    candidate_by_id = {
        candidate.video_id: candidate
        for candidate in candidates
    }

    print("\nAssessment completed successfully:")

    for assessment in result.assessments:
        candidate = candidate_by_id[assessment.video_id]
        average_score = (
            assessment.relevance_score
            + assessment.learner_fit_score
            + assessment.constraint_fit_score
        ) / 3

        print(f"\n- {candidate.title}")
        print(f"  Average score: {average_score:.1f}/10")
        print(
            f"  Evidence: {assessment.evidence_source}, "
            f"confidence={assessment.confidence:.2f}"
        )
        print(f"  Reason: {assessment.inclusion_reason}")

        if assessment.concerns:
            print(f"  Concerns: {'; '.join(assessment.concerns)}")

    print(f"\nStructured result saved to {output_path}")


if __name__ == "__main__":
    main()