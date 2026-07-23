from src.models import (
    CandidateAssessmentBatch,
    Curriculum,
    CurriculumDraft,
    LearningRequest,
    RejectedVideo,
    SelectedVideo,
    VideoCandidate,
)


def finalize_curriculum(
    request: LearningRequest,
    candidates: list[VideoCandidate],
    assessments: CandidateAssessmentBatch,
    draft: CurriculumDraft,
) -> Curriculum:
    """Restore trusted video facts and calculate the final curriculum budget."""

    assessment_by_id = {
        assessment.video_id: assessment
        for assessment in assessments.assessments
    }

    selected_videos = []

    for selected_draft in sorted(
        draft.selected_videos,
        key=lambda item: item.order,
    ):
        candidate = candidates[
            selected_draft.candidate_number - 1
        ]
        assessment = assessment_by_id[candidate.video_id]

        if candidate.duration_seconds is None:
            raise RuntimeError(
                f"Selected video has unknown duration: "
                f"{candidate.video_id}"
            )

        selected_videos.append(
            SelectedVideo(
                video_id=candidate.video_id,
                title=candidate.title,
                url=candidate.url,
                duration_seconds=candidate.duration_seconds,
                order=selected_draft.order,
                curriculum_role=selected_draft.curriculum_role,
                added_topics=selected_draft.added_topics,
                inclusion_reason=selected_draft.inclusion_reason,
                evidence_source=assessment.evidence_source,
                confidence=assessment.confidence,
            )
        )

    rejected_videos = []

    for rejected_draft in draft.rejected_videos:
        candidate = candidates[
            rejected_draft.candidate_number - 1
        ]

        rejected_videos.append(
            RejectedVideo(
                video_id=candidate.video_id,
                title=candidate.title,
                rejection_category=(
                    rejected_draft.rejection_category
                ),
                rejection_reason=(
                    rejected_draft.rejection_reason
                ),
            )
        )

    total_duration_seconds = sum(
        video.duration_seconds
        for video in selected_videos
    )
    budget_seconds = request.time_budget_minutes * 60
    remaining_budget_seconds = (
        budget_seconds - total_duration_seconds
    )

    if remaining_budget_seconds < 0:
        raise RuntimeError(
            "Final curriculum exceeds the learner's budget."
        )

    return Curriculum(
        persona_id=request.persona_id,
        title=draft.title,
        selected_videos=selected_videos,
        rejected_videos=rejected_videos,
        covered_topics=draft.covered_topics,
        uncovered_topics=draft.uncovered_topics,
        total_duration_seconds=total_duration_seconds,
        budget_seconds=budget_seconds,
        remaining_budget_seconds=remaining_budget_seconds,
        limitations=draft.limitations,
    )