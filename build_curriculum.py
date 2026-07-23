import json
from pathlib import Path

from src.agent import create_curriculum_draft
from src.curriculum import finalize_curriculum
from src.models import (
    CandidateAssessmentBatch,
    LearningRequest,
    SearchPlan,
    VideoCandidate,
)


def format_minutes(seconds: int) -> str:
    minutes = seconds // 60
    remaining_seconds = seconds % 60

    if remaining_seconds:
        return f"{minutes}m {remaining_seconds}s"

    return f"{minutes}m"


def main() -> None:
    context_path = Path("tmp/assessment_context.json")
    assessment_path = Path("tmp/assessment_result.json")

    if not context_path.exists():
        raise FileNotFoundError(
            f"Missing assessment context: {context_path}"
        )

    if not assessment_path.exists():
        raise FileNotFoundError(
            f"Missing assessment result: {assessment_path}"
        )

    context = json.loads(
        context_path.read_text(encoding="utf-8")
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

    assessments = CandidateAssessmentBatch.model_validate_json(
        assessment_path.read_text(encoding="utf-8")
    )

    print(
        f"Loaded {len(candidates)} candidates and "
        f"{len(assessments.assessments)} assessments."
    )
    print("Creating a globally compared curriculum draft...")

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

    output_path = Path("tmp/curriculum_result.json")
    output_path.write_text(
        curriculum.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print(f"\n{curriculum.title}")
    print(
        f"Total duration: "
        f"{format_minutes(curriculum.total_duration_seconds)}"
    )
    print(
        f"Remaining budget: "
        f"{format_minutes(curriculum.remaining_budget_seconds)}"
    )

    print("\nSelected videos:")

    for video in curriculum.selected_videos:
        print(
            f"\n{video.order}. {video.title} "
            f"({format_minutes(video.duration_seconds)})"
        )
        print(f"   Role: {video.curriculum_role}")
        print(
            f"   Adds: {', '.join(video.added_topics) or 'Unspecified'}"
        )
        print(f"   Reason: {video.inclusion_reason}")
        print(
            f"   Evidence: {video.evidence_source}, "
            f"confidence={video.confidence:.2f}"
        )
        print(f"   URL: {video.url}")

    print("\nRejected candidates:")

    for video in curriculum.rejected_videos:
        print(
            f"- {video.title} [{video.rejection_category}]: "
            f"{video.rejection_reason}"
        )

    print("\nCovered topics:")
    for topic in curriculum.covered_topics:
        print(f"- {topic}")

    print("\nUncovered or unverified topics:")
    for topic in curriculum.uncovered_topics:
        print(f"- {topic}")

    print("\nLimitations:")
    for limitation in curriculum.limitations:
        print(f"- {limitation}")

    print(f"\nStructured result saved to {output_path}")


if __name__ == "__main__":
    main()