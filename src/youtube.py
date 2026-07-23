from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL

from src.models import VideoCandidate, VideoEvidence
from yt_dlp import YoutubeDL

from src.models import VideoCandidate


def search_youtube(query: str, max_results: int = 5) -> list[VideoCandidate]:
    """Search YouTube without downloading any video content."""

    options = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
    }

    search_expression = f"ytsearch{max_results}:{query}"

    with YoutubeDL(options) as youtube:
        result = youtube.extract_info(search_expression, download=False)

    candidates: list[VideoCandidate] = []

    for entry in result.get("entries", []):
        if not entry or not entry.get("id") or not entry.get("title"):
            continue

        duration = entry.get("duration")

        candidates.append(
            VideoCandidate(
                video_id=entry["id"],
                title=entry["title"],
                url=f"https://www.youtube.com/watch?v={entry['id']}",
                duration_seconds=int(duration) if duration is not None else None,
                channel=entry.get("channel") or entry.get("uploader"),
                discovery_query=query,
            )
        )

    return candidates

def search_multiple_queries(
    queries: list[str],
    results_per_query: int = 5,
) -> list[VideoCandidate]:
    """Search several queries and remove duplicate videos by YouTube ID."""

    unique_candidates: dict[str, VideoCandidate] = {}

    for query in queries:
        for candidate in search_youtube(query, results_per_query):
            if candidate.video_id not in unique_candidates:
                unique_candidates[candidate.video_id] = candidate

    return list(unique_candidates.values())
def get_video_evidence(
    candidate: VideoCandidate,
    max_characters: int = 12_000,
) -> VideoEvidence:
    """Retrieve transcript evidence, falling back transparently to metadata."""

    try:
        transcript = YouTubeTranscriptApi().fetch(candidate.video_id)
        transcript_text = " ".join(segment.text for segment in transcript)

        return VideoEvidence(
            video_id=candidate.video_id,
            evidence_text=transcript_text[:max_characters],
            evidence_source="transcript",
        )

    except Exception as error:
        duration_text = (
            f"{candidate.duration_seconds} seconds"
            if candidate.duration_seconds is not None
            else "unknown"
        )

        metadata_text = (
            f"Title: {candidate.title}\n"
            f"Channel: {candidate.channel or 'unknown'}\n"
            f"Duration: {duration_text}\n"
        )

        return VideoEvidence(
            video_id=candidate.video_id,
            evidence_text=metadata_text,
            evidence_source="metadata",
            retrieval_error=type(error).__name__,
        )