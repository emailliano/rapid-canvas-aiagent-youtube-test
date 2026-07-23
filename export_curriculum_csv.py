import csv
import json
from pathlib import Path


CSV_COLUMNS = [
    "status",
    "order",
    "video_id",
    "title",
    "url",
    "duration_seconds",
    "duration_minutes",
    "curriculum_role",
    "added_topics",
    "decision_category",
    "decision_reason",
    "evidence_source",
    "confidence",
]


def main() -> None:
    curriculum_path = Path("tmp/curriculum_result.json")
    context_path = Path("tmp/assessment_context.json")
    assessment_path = Path("tmp/assessment_result.json")

    output_path = Path(
        "evaluation/baselines/"
        "01_weekend_react_dev_curriculum.csv"
    )

    curriculum = json.loads(
        curriculum_path.read_text(encoding="utf-8")
    )
    context = json.loads(
        context_path.read_text(encoding="utf-8")
    )
    assessment_result = json.loads(
        assessment_path.read_text(encoding="utf-8")
    )

    candidate_by_id = {
        candidate["video_id"]: candidate
        for candidate in context["candidates"]
    }
    assessment_by_id = {
        assessment["video_id"]: assessment
        for assessment in assessment_result["assessments"]
    }

    rows = []

    for video in curriculum["selected_videos"]:
        rows.append(
            {
                "status": "selected",
                "order": video["order"],
                "video_id": video["video_id"],
                "title": video["title"],
                "url": video["url"],
                "duration_seconds": video["duration_seconds"],
                "duration_minutes": round(
                    video["duration_seconds"] / 60,
                    2,
                ),
                "curriculum_role": video["curriculum_role"],
                "added_topics": " | ".join(
                    video["added_topics"]
                ),
                "decision_category": "selected",
                "decision_reason": video["inclusion_reason"],
                "evidence_source": video["evidence_source"],
                "confidence": video["confidence"],
            }
        )

    for video in curriculum["rejected_videos"]:
        candidate = candidate_by_id[video["video_id"]]
        assessment = assessment_by_id[video["video_id"]]

        duration_seconds = candidate["duration_seconds"]

        rows.append(
            {
                "status": "rejected",
                "order": "",
                "video_id": video["video_id"],
                "title": video["title"],
                "url": candidate["url"],
                "duration_seconds": (
                    duration_seconds
                    if duration_seconds is not None
                    else ""
                ),
                "duration_minutes": (
                    round(duration_seconds / 60, 2)
                    if duration_seconds is not None
                    else ""
                ),
                "curriculum_role": "",
                "added_topics": "",
                "decision_category": video[
                    "rejection_category"
                ],
                "decision_reason": video[
                    "rejection_reason"
                ],
                "evidence_source": assessment[
                    "evidence_source"
                ],
                "confidence": assessment["confidence"],
            }
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=CSV_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Wrote {len(rows)} curriculum decisions to "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()