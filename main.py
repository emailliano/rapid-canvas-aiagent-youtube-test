import argparse
import json
from pathlib import Path

from src.agent import assess_candidates_in_batches, create_search_plan
from src.models import LearningRequest
from src.youtube import get_video_evidence, search_multiple_queries


def load_request(input_path: str) -> LearningRequest:
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    return LearningRequest.model_validate_json(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a personalized YouTube learning curriculum."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a learner scenario JSON file.",
    )
    args = parser.parse_args()

    request = load_request(args.input)

    print(f"\nPersona: {request.persona_id}")
    print(f"Goal: {request.goal}")
    print(f"Time budget: {request.time_budget_minutes} minutes")

    print("\nCreating search plan...")
    plan = create_search_plan(request)

    print("\nRequired topics:")
    for topic in plan.required_topics:
        print(f"- {topic}")

    print("\nExcluded topics:")
    for topic in plan.excluded_topics:
        print(f"- {topic}")

    print("\nSearch queries:")
    for query in plan.search_queries:
        print(f"- {query}")

    print("\nSearching YouTube...")
    candidates = search_multiple_queries(
        plan.search_queries,
        results_per_query=3,
    )

    print(f"\nDiscovered {len(candidates)} unique candidates:")
    for candidate in candidates:
        duration = (
            f"{candidate.duration_seconds // 60} min"
            if candidate.duration_seconds is not None
            else "unknown duration"
        )
        print(f"- [{duration}] {candidate.title}")
    maximum_duration_seconds = request.time_budget_minutes * 60

    duration_rejected = [
        candidate
        for candidate in candidates
        if (
            candidate.duration_seconds is not None
            and candidate.duration_seconds > maximum_duration_seconds
        )
    ]

    candidates = [
        candidate
        for candidate in candidates
        if (
            candidate.duration_seconds is None
            or candidate.duration_seconds <= maximum_duration_seconds
        )
    ]

    if duration_rejected:
        print("\nRejected before assessment because duration exceeds budget:")
        for candidate in duration_rejected:
            print(
                f"- [{candidate.duration_seconds // 60} min] "
                f"{candidate.title}"
            )

    print(
        f"\n{len(candidates)} candidates remain eligible "
        f"for assessment."
    )
    print("\nRetrieving evidence...")
    evidence = [
        get_video_evidence(candidate, max_characters=6_000)
        for candidate in candidates
    ]

    transcript_count = sum(
        item.evidence_source == "transcript"
        for item in evidence
    )
    metadata_count = sum(
        item.evidence_source == "metadata"
        for item in evidence
    )

    print(
        f"Evidence retrieved: {transcript_count} transcripts, "
        f"{metadata_count} metadata fallbacks"
    )

    batch_size = 5
    checkpoint_path = Path("tmp/assessment_context.json")
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    checkpoint_payload = {
        "request": request.model_dump(),
        "search_plan": plan.model_dump(),
        "candidates": [
            candidate.model_dump()
            for candidate in candidates
        ],
        "evidence": [
            item.model_dump()
            for item in evidence
        ],
    }

    checkpoint_path.write_text(
        json.dumps(checkpoint_payload, indent=2),
        encoding="utf-8",
    )

    print(
        f"Assessment checkpoint saved to {checkpoint_path}"
    )

    print(
        f"\nAssessing {len(candidates)} candidates "
        f"in batches of up to {batch_size}..."
    )

    assessment_batch = assess_candidates_in_batches(
        request=request,
        plan=plan,
        candidates=candidates,
        evidence=evidence,
        batch_size=batch_size,
    )

    candidate_by_id = {
        candidate.video_id: candidate
        for candidate in candidates
    }

    ranked_assessments = sorted(
        assessment_batch.assessments,
        key=lambda assessment: (
            assessment.relevance_score
            + assessment.learner_fit_score
            + assessment.constraint_fit_score
        ),
        reverse=True,
    )

    print("\nCandidate assessments:")

    for assessment in ranked_assessments:
        candidate = candidate_by_id[assessment.video_id]
        average_score = (
            assessment.relevance_score
            + assessment.learner_fit_score
            + assessment.constraint_fit_score
        ) / 3

        print(f"\n- {candidate.title}")
        print(f"  Average score: {average_score:.1f}/10")
        print(
            "  Scores: "
            f"relevance={assessment.relevance_score}, "
            f"learner_fit={assessment.learner_fit_score}, "
            f"constraint_fit={assessment.constraint_fit_score}"
        )
        print(
            f"  Evidence: {assessment.evidence_source}, "
            f"confidence={assessment.confidence:.2f}"
        )
        print(f"  Reason: {assessment.inclusion_reason}")

        if assessment.concerns:
            print(f"  Concerns: {'; '.join(assessment.concerns)}")


if __name__ == "__main__":
    main()