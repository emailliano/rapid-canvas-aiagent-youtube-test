import argparse
from pathlib import Path

from evaluation.evaluate import evaluate_curriculum
from src.agent import (
    assess_candidates_in_batches,
    create_curriculum_draft,
    create_search_plan,
)
from src.curriculum import finalize_curriculum
from src.models import LearningRequest
from src.youtube import (
    get_video_evidence,
    search_multiple_queries,
)


def load_request(input_path: str) -> LearningRequest:
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Input file not found: {path}"
        )

    return LearningRequest.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def format_duration(seconds: int) -> str:
    minutes, remaining_seconds = divmod(seconds, 60)

    if remaining_seconds:
        return f"{minutes}m {remaining_seconds}s"

    return f"{minutes}m"


def save_result(
    output_path: Path,
    json_content: str,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json_content,
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build and evaluate a personalized "
            "YouTube learning curriculum."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a learner-scenario JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for generated artifacts.",
    )
    args = parser.parse_args()

    request = load_request(args.input)
    output_dir = (
        Path(args.output_dir) / request.persona_id
    )

    print(f"\nPersona: {request.persona_id}")
    print(f"Goal: {request.goal}")
    print(
        f"Budget: {request.time_budget_minutes} minutes"
    )

    print("\n1. Creating a personalized search plan...")
    plan = create_search_plan(request)

    print("\nSearch queries:")
    for query in plan.search_queries:
        print(f"- {query}")

    print("\n2. Discovering YouTube candidates...")
    discovered_candidates = search_multiple_queries(
        plan.search_queries,
        results_per_query=5,
    )

    budget_seconds = request.time_budget_minutes * 60

    candidates = [
        candidate
        for candidate in discovered_candidates
        if (
            candidate.duration_seconds is not None
            and candidate.duration_seconds <= budget_seconds
        )
    ]

    excluded_before_assessment = [
        candidate
        for candidate in discovered_candidates
        if candidate not in candidates
    ]

    print(
        f"Discovered {len(discovered_candidates)} unique videos; "
        f"{len(candidates)} have a known duration and can fit "
        "inside the total budget."
    )

    if excluded_before_assessment:
        print("\nExcluded before assessment:")

        for candidate in excluded_before_assessment:
            duration = (
                format_duration(candidate.duration_seconds)
                if candidate.duration_seconds is not None
                else "unknown duration"
            )
            print(f"- [{duration}] {candidate.title}")

    if not candidates:
        raise RuntimeError(
            "No eligible YouTube candidates were discovered."
        )

    print("\n3. Retrieving the best available evidence...")
    evidence = [
        get_video_evidence(
            candidate,
            max_characters=6_000,
        )
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
        f"Evidence: {transcript_count} transcripts, "
        f"{metadata_count} metadata fallbacks."
    )

    print("\n4. Assessing candidates...")
    assessments = assess_candidates_in_batches(
        request=request,
        plan=plan,
        candidates=candidates,
        evidence=evidence,
        batch_size=5,
    )

    print("\n5. Selecting a complementary curriculum...")
    draft = create_curriculum_draft(
        request=request,
        plan=plan,
        candidates=candidates,
        assessments=assessments,
    )

    curriculum = finalize_curriculum(
        request=request,
        candidates=candidates,
        assessments=assessments,
        draft=draft,
    )

    print("\n6. Evaluating the curriculum...")
    evaluation = evaluate_curriculum(
        request=request,
        curriculum=curriculum,
        expected_candidate_count=len(candidates),
    )

    save_result(
        output_dir / "search_plan.json",
        plan.model_dump_json(indent=2),
    )
    save_result(
        output_dir / "candidate_assessments.json",
        assessments.model_dump_json(indent=2),
    )
    save_result(
        output_dir / "curriculum.json",
        curriculum.model_dump_json(indent=2),
    )
    save_result(
        output_dir / "evaluation.json",
        evaluation.model_dump_json(indent=2),
    )

    print(f"\n{curriculum.title}")
    print(
        f"Duration: "
        f"{format_duration(curriculum.total_duration_seconds)} "
        f"of {request.time_budget_minutes}m"
    )

    print("\nSelected videos:")

    for video in curriculum.selected_videos:
        print(
            f"\n{video.order}. {video.title} "
            f"({format_duration(video.duration_seconds)})"
        )
        print(f"   Role: {video.curriculum_role}")
        print(f"   Reason: {video.inclusion_reason}")
        print(
            f"   Evidence: {video.evidence_source}, "
            f"confidence={video.confidence:.2f}"
        )
        print(f"   URL: {video.url}")

    flagged_checks = [
        check
        for check in evaluation.checks
        if not check.passed
    ]

    print(
        f"\nTechnical validity: "
        f"{'PASS' if evaluation.overall_passed else 'FAIL'}"
    )

    if flagged_checks:
        print("\nEvaluation flags:")

        for check in flagged_checks:
            print(
                f"- [{check.severity}] "
                f"{check.name}: {check.detail}"
            )

    print(f"\nArtifacts saved to: {output_dir}")


if __name__ == "__main__":
    main()