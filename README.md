# Learning Curriculum Builder

An AI agent that builds a personalized YouTube learning curriculum from:

- a concrete learning goal;
- a time budget in minutes;
- the learner's background;
- topics they already know;
- topics they need to learn;
- learning preferences and constraints.

The agent discovers candidate videos, retrieves the strongest available
evidence, assesses every candidate, selects a complementary sequence, and
evaluates the final curriculum.

## Example

The reference persona is a Python backend developer who wants to build a small
React application over a weekend.

The agent should:

- skip general JavaScript material the learner already knows;
- introduce React and Vite;
- prioritize project-based instruction;
- include a project similar to the requested application;
- avoid superficial content;
- remain within the six-hour budget.

## Requirements

- Python 3.12
- An OpenAI API key
- Internet access for YouTube discovery

## Setup

Clone the repository and enter its directory:

```bash
git clone https://github.com/emailliano/rapid-canvas-aiagent-youtube-test.git
cd rapid-canvas-aiagent-youtube-test
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate it with:

```powershell
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

Add your API key:

```text
OPENAI_API_KEY=your_openai_api_key_here
```

Alternatively, configure `OPENAI_API_KEY` as an environment variable or
Codespaces secret.

The model can be overridden without changing source code:

```text
OPENAI_MODEL=your_model_name
```

Do not commit `.env` or an API key.

## Run the agent

From the repository root:

```bash
python main.py \
  --input test_set/01_weekend_react_dev.json \
  --output-dir outputs
```

This is the complete end-to-end command after setup.

The agent creates:

```text
outputs/weekend_react_dev/
├── search_plan.json
├── candidate_assessments.json
├── curriculum.json
└── evaluation.json
```

The `persona_id` determines the subdirectory, so different scenarios do not
overwrite one another when the same output root is used.

## Input format

Each scenario is a JSON document:

```json
{
  "persona_id": "weekend_react_dev",
  "goal": "Build a small React app this weekend, something like a habit tracker with local storage",
  "time_budget_minutes": 360,
  "user_context": {
    "background": "Python backend engineer, 5 years experience",
    "known": [
      "JavaScript fundamentals",
      "HTTP, REST, JSON",
      "Git",
      "npm"
    ],
    "unknown": [
      "React",
      "JSX",
      "Vite tooling",
      "React hooks",
      "Component patterns"
    ],
    "constraints": "I prefer project-based content. Avoid pure-theory lectures and 'in 100 seconds' surface intros."
  }
}
```

No source-code changes are required to run a new persona. Create another JSON
file with the same structure and pass its path to `--input`.

## Pipeline

The application runs six stages:

1. **Search planning**
   Convert the learner request into required topics, exclusions, and
   complementary YouTube search queries.

2. **Candidate discovery**
   Search YouTube through yt-dlp, normalize metadata, deduplicate video IDs,
   and exclude candidates that cannot fit the hard budget.

3. **Evidence retrieval**
   Attempt transcript retrieval first. If YouTube blocks it, preserve the
   retrieval error and fall back to title, channel, and duration metadata.

4. **Candidate assessment**
   Assess every candidate for goal relevance, learner fit, constraint fit,
   apparent topic coverage, concerns, evidence quality, and confidence.

5. **Curriculum selection**
   Select a ranked, complementary set with explicit curriculum roles,
   inclusion reasons, rejections, and declared coverage gaps.

6. **Finalization and evaluation**
   Reconstruct the original candidate identities, recalculate all duration
   arithmetic, validate accounting, and produce separate technical,
   curriculum-quality, and evidence verdicts.

## Architecture

```text
.
├── main.py
├── requirements.txt
├── src/
│   ├── agent.py
│   ├── curriculum.py
│   ├── models.py
│   └── youtube.py
├── evaluation/
│   ├── evaluate.py
│   ├── baselines/
│   └── results/
└── test_set/
```

### `main.py`

The one-command orchestrator. It loads the scenario, runs every pipeline stage,
prints a readable result, and saves all artifacts.

### `src/models.py`

Pydantic models for learner requests, search plans, video candidates, evidence,
candidate assessments, curriculum drafts, final curricula, and evaluation
reports.

### `src/agent.py`

OpenAI structured-output calls for:

- personalized search planning;
- evidence-aware candidate assessment;
- complementary curriculum selection.

### `src/youtube.py`

YouTube discovery through yt-dlp and transcript retrieval through
`youtube-transcript-api`, with explicit metadata fallback.

### `src/curriculum.py`

Deterministic conversion of model-facing candidate numbers into original
videos, URLs, durations, and final curriculum records.

### `evaluation/evaluate.py`

Deterministic technical checks plus explainable curriculum-quality and
evidence-quality heuristics.

## Significant design decisions

### Structured outputs with Pydantic

Every model-facing stage returns a validated schema. This makes malformed
responses explicit and keeps data contracts readable.

### Candidate numbers inside prompts

The model receives consecutive candidate numbers instead of being asked to
reproduce opaque YouTube IDs. Deterministic code maps the numbers back to the
original candidates.

This was introduced after early model responses omitted or mishandled
identifiers.

### Batched candidate assessment

Candidate pools are assessed in small batches. The code verifies that every
candidate is assessed exactly once and rejects missing, unexpected, or
duplicate assessments.

### Evidence-aware fallback

Transcripts are preferred. When retrieval fails, the system does not stop or
invent content. It:

- records the retrieval error;
- marks the evidence as metadata;
- caps confidence;
- requires cautious reasoning;
- reports limited evidence quality.

### Model judgment plus deterministic validation

The language model handles semantic tasks:

- translating learner needs into searches;
- judging relevance and fit;
- proposing a complementary sequence;
- explaining inclusions and rejections.

Code handles invariants:

- video identity;
- candidate accounting;
- uniqueness;
- ordering;
- duration arithmetic;
- budget compliance;
- evidence-source consistency;
- confidence caps.

### Separate evaluation verdicts

The final report separates:

- `Technical validity`
- `Curriculum adequacy`
- `Evidence quality`

A valid curriculum can therefore remain usable while being marked for review
because its detailed content is not verifiable.

### Preferred count and duration, not forced padding

The selection prompt prefers:

- 4 to 6 videos;
- approximately 67% to 90% of the available budget.

The hard requirement is only that the budget is not exceeded. The system should
not add weak or repetitive material merely to reach a duration target.

### Simple architecture

The final solution intentionally avoids a workflow framework, database, cache
service, or multiple recovery scripts. The assignment favors readable code,
and these additions did not solve the primary constraint: access to reliable
content evidence.

## Evaluation

Evaluation is the primary design focus of the project.

The evaluator checks:

### Technical validity

- budget compliance;
- duration arithmetic;
- remaining-budget arithmetic;
- unique video accounting;
- consecutive ordering;
- complete selected/rejected accounting.

### Curriculum adequacy

- preferred video count;
- budget utilization;
- conflicts with surface-content constraints;
- presence of a foundation and project spine;
- declared uncovered or unverified topics.

### Evidence quality

- transcript versus metadata evidence;
- retrieval errors;
- evidence-consistent confidence;
- cautious metadata-grounded reasoning.

See [EVALUATION.md](EVALUATION.md) for the full methodology, five-scenario
results, disagreements with human judgment, failure cases, discarded signals,
and limitations.

## Test scenarios

The repository includes five scenarios:

| File | Persona |
|---|---|
| `01_weekend_react_dev.json` | Python backend developer learning React through a weekend project |
| `02_python_data_science_beginner.json` | Spreadsheet analyst learning Python data analysis |
| `03_aws_data_science_transition.json` | Data scientist moving a workflow to AWS and SageMaker |
| `04_machine_learning_from_scratch.json` | Mathematical learner implementing ML algorithms with NumPy |
| `05_python_rag_application.json` | Python backend developer building a document-grounded RAG application |

Each scenario has a preserved curriculum under `evaluation/baselines/` and a
corresponding evaluation under `evaluation/results/`.

## Baseline results

| Persona | Videos | Utilization | Technical | Adequacy | Evidence |
|---|---:|---:|---|---|---|
| Weekend React developer | 5 | 86.0% | PASS | NEEDS REVISION | LIMITED |
| Python data-science beginner | 4 | 85.4% | PASS | NEEDS REVISION | LIMITED |
| AWS data-science transition | 6 | 71.9% | PASS | NEEDS REVISION | LIMITED |
| Machine learning from scratch | 6 | 71.5% | PASS | NEEDS REVISION | LIMITED |
| Python RAG application | 6 | 70.8% | PASS | NEEDS REVISION | LIMITED |

All five baselines passed deterministic technical validation. `NEEDS REVISION`
primarily reflects uncovered or metadata-unverified topics rather than
structural failure.

## Limitations

### Transcript access

YouTube blocked transcript retrieval from the Codespaces environment with
`RequestBlocked`. yt-dlp subtitle retrieval also encountered bot verification.
All preserved baselines therefore use metadata evidence.

### Metadata cannot verify instruction

A title can indicate relevance but cannot prove:

- teaching quality;
- exact topic coverage;
- code correctness;
- pacing;
- project completeness;
- content freshness.

### Search and model nondeterminism

YouTube search results and model judgments can vary between runs. Saved
baselines document observed behavior; they are not golden outputs that every
execution must reproduce exactly.

### Heuristic evaluation

Foundation, project-spine, redundancy, and surface-content checks are useful
signals, not complete pedagogical judgments. The evaluation documents cases
where these heuristics disagree with human review.

### No learner-outcome measurement

The project evaluates structural validity and evidence-aware plausibility. It
does not measure whether a learner completes the curriculum or achieves the
goal.

### Discovery scope

The current version does not use:

- the YouTube Data API;
- comments;
- Reddit or other communities;
- external course platforms;
- content embeddings for semantic deduplication.

## What I would do with more time

### 1. Add descriptions and chapters

This is the highest-priority extension because it improves content evidence
when transcripts are unavailable without requiring a full external discovery
system.

### 2. Build a human-reviewed gold set

Annotate candidate relevance, topic coverage, redundancy, ordering, confidence,
and preferred curricula. This would support measurable agreement with human
curators.

### 3. Compare prompts or models

Run blind pairwise comparisons between curriculum-selection strategies and
report preference, cost, latency, and failure rates.

### 4. Add content-level deduplication

Use transcripts, descriptions, chapters, or embeddings to detect conceptual
overlap rather than relying on title similarity.

### 5. Separate discovery and selection quality

Track whether each required topic was searched, discovered, assessed,
selected, and verified. This would reveal whether a gap originated in
discovery or final selection.

### 6. Instrument cost and latency

Measure token usage, API cost, stage latency, and retry rate before projecting
operating cost at scale.

### 7. Evaluate learner outcomes

Measure completion, actual time spent, project success, knowledge gains, and
which recommendations learners skip or replace.

## Security

- Keep `OPENAI_API_KEY` in `.env`, an environment variable, or a secret store.
- Never commit `.env`.
- `.env`, virtual environments, temporary files, caches, logs, and generated
  output directories are ignored by Git.

## Repository

Public repository:

<https://github.com/emailliano/rapid-canvas-aiagent-youtube-test>

The final verified submission commit should be tagged:

```text
v1-submission
```
