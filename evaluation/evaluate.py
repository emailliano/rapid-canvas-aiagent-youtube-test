import argparse
from pathlib import Path

from src.models import (
    Curriculum,
    DeterministicEvaluation,
    EvaluationCheck,
    LearningRequest,
)

ADEQUACY_CHECK_NAMES = {
    "recommended_video_count",
    "budget_utilization",
    "curriculum_backbone",
    "surface_content_constraint",
    "declared_topic_coverage",
}


def evaluate_curriculum(
    request: LearningRequest,
    curriculum: Curriculum,
    expected_candidate_count: int | None = None,
) -> DeterministicEvaluation:
    """Evaluate objective curriculum properties without using an LLM."""

    checks: list[EvaluationCheck] = []

    selected = curriculum.selected_videos
    rejected = curriculum.rejected_videos

    calculated_duration = sum(
        video.duration_seconds
        for video in selected
    )
    calculated_remaining = (
        curriculum.budget_seconds - calculated_duration
    )

    checks.append(
        EvaluationCheck(
            name="budget_compliance",
            passed=calculated_duration <= curriculum.budget_seconds,
            severity="error",
            detail=(
                f"Selected {calculated_duration} seconds from a "
                f"{curriculum.budget_seconds}-second budget."
            ),
        )
    )

    checks.append(
        EvaluationCheck(
            name="duration_arithmetic",
            passed=(
                calculated_duration
                == curriculum.total_duration_seconds
            ),
            severity="error",
            detail=(
                f"Calculated duration is {calculated_duration}; "
                f"reported duration is "
                f"{curriculum.total_duration_seconds}."
            ),
        )
    )

    checks.append(
        EvaluationCheck(
            name="remaining_budget_arithmetic",
            passed=(
                calculated_remaining
                == curriculum.remaining_budget_seconds
            ),
            severity="error",
            detail=(
                f"Calculated remaining budget is "
                f"{calculated_remaining}; reported value is "
                f"{curriculum.remaining_budget_seconds}."
            ),
        )
    )

    all_ids = [
        video.video_id
        for video in selected
    ] + [
        video.video_id
        for video in rejected
    ]

    checks.append(
        EvaluationCheck(
            name="unique_candidate_accounting",
            passed=len(all_ids) == len(set(all_ids)),
            severity="error",
            detail=(
                f"Found {len(all_ids)} curriculum entries and "
                f"{len(set(all_ids))} unique video IDs."
            ),
        )
    )

    expected_orders = list(
        range(1, len(selected) + 1)
    )
    actual_orders = [
        video.order
        for video in selected
    ]

    checks.append(
        EvaluationCheck(
            name="consecutive_order",
            passed=actual_orders == expected_orders,
            severity="error",
            detail=(
                f"Expected orders {expected_orders}; "
                f"received {actual_orders}."
            ),
        )
    )

    if expected_candidate_count is not None:
        checks.append(
            EvaluationCheck(
                name="candidate_accounting",
                passed=(
                    len(selected) + len(rejected)
                    == expected_candidate_count
                ),
                severity="error",
                detail=(
                    f"Selected {len(selected)} and rejected "
                    f"{len(rejected)} from an expected "
                    f"{expected_candidate_count} candidates."
                ),
            )
        )

    selected_count = len(selected)

    checks.append(
        EvaluationCheck(
            name="recommended_video_count",
            passed=4 <= selected_count <= 6,
            severity="warning",
            detail=(
                f"Selected {selected_count} videos; the assignment's "
                f"reference output suggests 4 to 6 when feasible."
            ),
        )
    )

    utilization = (
        calculated_duration / curriculum.budget_seconds
        if curriculum.budget_seconds
        else 0.0
    )

    checks.append(
        EvaluationCheck(
            name="budget_utilization",
            passed=utilization >= 0.67,
            severity="warning",
            detail=(
                f"The curriculum uses {utilization:.1%} of the "
                "available learning budget; the preferred minimum "
                "for a project-based curriculum is 67%."
            ),
        )
    )

    foundation_text = " ".join(
        text
        for video in selected
        for text in (
            video.curriculum_role,
            *video.added_topics,
        )
    ).lower()
    project_text = " ".join(
        text
        for video in selected
        for text in (
            video.title,
            video.curriculum_role,
            *video.added_topics,
        )
    ).lower()

    foundation_present = any(
        term in foundation_text
        for term in (
            "setup",
            "foundation",
            "fundamental",
            "getting started",
            "tooling",
        )
    )
    project_present = any(
        term in project_text
        for term in (
            "project spine",
            "primary project",
            "complete project",
            "build-along",
            "build along",
            "project-based",
            "habit tracker",
            "to-do",
            "todo",
        )
    )
    backbone_passed = foundation_present and project_present

    checks.append(
        EvaluationCheck(
            name="curriculum_backbone",
            passed=backbone_passed,
            severity="warning",
            detail=(
                "The selected roles indicate both a foundation/setup "
                "resource and a project spine."
                if backbone_passed
                else (
                    "The selected titles and roles do not clearly "
                    "establish both a foundation/setup resource and "
                    "a primary project spine. This is a heuristic "
                    "check and does not verify video contents."
                )
            ),
        )
    )

    constraints = request.user_context.constraints.lower()
    avoids_surface_content = any(
        phrase in constraints
        for phrase in (
            "surface",
            "100 seconds",
            "very short",
            "short intro",
        )
    )

    surface_risk_videos = [
        video
        for video in selected
        if video.duration_seconds < 300
    ]

    surface_constraint_passed = not (
        avoids_surface_content and surface_risk_videos
    )

    checks.append(
        EvaluationCheck(
            name="surface_content_constraint",
            passed=surface_constraint_passed,
            severity="warning",
            detail=(
                "No selected video under five minutes conflicts with "
                "the learner's surface-content constraint."
                if surface_constraint_passed
                else (
                    "Potential surface-level selections: "
                    + ", ".join(
                        video.title
                        for video in surface_risk_videos
                    )
                )
            ),
        )
    )

    transcript_count = sum(
        video.evidence_source == "transcript"
        for video in selected
    )
    metadata_count = sum(
        video.evidence_source == "metadata"
        for video in selected
    )

    checks.append(
        EvaluationCheck(
            name="content_level_evidence",
            passed=transcript_count > 0,
            severity="info",
            detail=(
                f"Selected evidence contains {transcript_count} "
                f"transcript-grounded and {metadata_count} "
                f"metadata-grounded videos."
            ),
        )
    )

    checks.append(
        EvaluationCheck(
            name="declared_topic_coverage",
            passed=not curriculum.uncovered_topics,
            severity="warning",
            detail=(
                "No uncovered topics were declared."
                if not curriculum.uncovered_topics
                else (
                    f"The curriculum declares "
                    f"{len(curriculum.uncovered_topics)} uncovered "
                    f"or unverified topic areas."
                )
            ),
        )
    )

    error_checks = [
        check
        for check in checks
        if check.severity == "error"
    ]
    overall_passed = all(
        check.passed
        for check in error_checks
    )

    return DeterministicEvaluation(
        persona_id=request.persona_id,
        overall_passed=overall_passed,
        checks=checks,
        metrics={
            "selected_video_count": selected_count,
            "rejected_video_count": len(rejected),
            "total_duration_seconds": calculated_duration,
            "budget_seconds": curriculum.budget_seconds,
            "remaining_budget_seconds": calculated_remaining,
            "budget_utilization": round(utilization, 4),
            "transcript_evidence_count": transcript_count,
            "metadata_evidence_count": metadata_count,
            "declared_uncovered_topic_count": len(
                curriculum.uncovered_topics
            ),
        },
    )


def evaluation_verdicts(
    evaluation: DeterministicEvaluation,
) -> tuple[str, str, str]:
    """Summarize technical, curriculum, and evidence quality."""

    technical_validity = (
        "PASS"
        if evaluation.overall_passed
        else "FAIL"
    )

    adequacy_failed = any(
        (
            check.name in ADEQUACY_CHECK_NAMES
            and not check.passed
        )
        for check in evaluation.checks
    )
    curriculum_adequacy = (
        "NEEDS REVISION"
        if adequacy_failed
        else "PASS"
    )

    selected_count = int(
        evaluation.metrics["selected_video_count"]
    )
    transcript_count = int(
        evaluation.metrics["transcript_evidence_count"]
    )

    if selected_count > 0 and transcript_count == selected_count:
        evidence_quality = "STRONG"
    elif transcript_count > 0:
        evidence_quality = "MIXED"
    else:
        evidence_quality = "LIMITED"

    return (
        technical_validity,
        curriculum_adequacy,
        evidence_quality,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a generated learning curriculum."
    )
    parser.add_argument(
        "--request",
        required=True,
        help="Path to the learner-request JSON file.",
    )
    parser.add_argument(
        "--curriculum",
        required=True,
        help="Path to the generated curriculum JSON file.",
    )
    parser.add_argument(
        "--expected-candidates",
        type=int,
        default=None,
        help="Number of eligible candidates considered.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path where the evaluation JSON will be written.",
    )
    args = parser.parse_args()

    request = LearningRequest.model_validate_json(
        Path(args.request).read_text(encoding="utf-8")
    )
    curriculum = Curriculum.model_validate_json(
        Path(args.curriculum).read_text(encoding="utf-8")
    )

    result = evaluate_curriculum(
        request=request,
        curriculum=curriculum,
        expected_candidate_count=args.expected_candidates,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )

    (
        technical_validity,
        curriculum_adequacy,
        evidence_quality,
    ) = evaluation_verdicts(result)

    print(
        f"Technical validity: {technical_validity}"
    )
    print(f"Curriculum adequacy: {curriculum_adequacy}")
    print(f"Evidence quality: {evidence_quality}")

    for check in result.checks:
        status = "PASS" if check.passed else "FLAG"

        print(
            f"[{status}] [{check.severity.upper()}] "
            f"{check.name}: {check.detail}"
        )

    print(f"\nEvaluation saved to {output_path}")


if __name__ == "__main__":
    main()