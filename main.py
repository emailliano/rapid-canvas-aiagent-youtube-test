import argparse
from pathlib import Path

from src.models import LearningRequest


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

    print(f"Persona: {request.persona_id}")
    print(f"Goal: {request.goal}")
    print(f"Time budget: {request.time_budget_minutes} minutes")
    print(f"Known topics: {', '.join(request.user_context.known)}")
    print(f"Learning gaps: {', '.join(request.user_context.unknown)}")


if __name__ == "__main__":
    main()