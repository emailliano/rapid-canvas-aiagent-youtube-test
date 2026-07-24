# Evaluation

## Evaluation goal

The agent is evaluated on whether it creates a personalized, feasible learning
sequence, not whether it returns popular videos.

I separate evaluation into three verdicts:

1. **Technical validity** - structural correctness and hard constraints.
2. **Curriculum adequacy** - personalization, sequence, complementarity, and
   practical usefulness.
3. **Evidence quality** - how strongly the available evidence supports claims
   about video content.

This separation matters because a curriculum can be technically valid and
useful while still requiring review when detailed content cannot be verified.

## What good output means

The assignment's reference React persona suggests:

- 4 to 6 ranked videos;
- React/Vite setup followed by a relevant project;
- no unnecessary JavaScript introductions;
- no surface-level content rejected by the learner;
- approximately five hours of material;
- concise inclusion reasons grounded in available evidence;
- visible confidence, rejected candidates, and redundancy reasoning.

I generalize this into six criteria:

- **Personalization:** use known topics, gaps, background, and constraints.
- **Goal alignment:** include a meaningful project or implementation spine.
- **Sequence:** introduce prerequisites before dependent work.
- **Complementarity:** each selection should serve a distinct role.
- **Feasibility:** stay within budget without padding with weak content.
- **Grounding:** do not claim more than the evidence supports.

## What is measured

### Deterministic technical checks

- Selected duration does not exceed the budget.
- Reported duration equals the sum of selected durations.
- Remaining-budget arithmetic is correct.
- Video IDs are unique.
- Selection order is consecutive from 1.
- Every candidate is selected or rejected, never both.
- Selected and rejected candidates account for the expected pool.

Any failed error-level check makes technical validity fail.

### Curriculum-quality heuristics

- Prefer 4 to 6 videos when feasible.
- Prefer at least 67% budget utilization for project-based curricula.
- Flag very short videos when they conflict with surface-content constraints.
- Look for both a foundation/setup resource and a project spine.
- Report topics declared uncovered or unverified.

These checks produce warnings rather than technical failures. A shorter,
coherent curriculum is better than one padded with irrelevant or repetitive
videos.

### Evidence checks

The system first attempts transcript retrieval and falls back to title, channel,
and duration metadata when transcripts are unavailable.

- Metadata confidence is capped at `0.55`.
- Transcript confidence is capped at `0.95`.
- Retrieval errors and evidence sources are preserved.
- Metadata-only reasons must use cautious language.

Evidence quality is reported as:

- `STRONG`: all selected resources are transcript-grounded.
- `MIXED`: transcript and metadata evidence are both present.
- `LIMITED`: all selected resources rely on metadata.

## Test scenarios

The five scenarios exercise different learner transitions:

| Scenario | Main challenge |
|---|---|
| Weekend React developer | Skip known JavaScript and build a project-oriented frontend path |
| Python data-science beginner | Balance Python basics, notebooks, data analysis, and visualization |
| AWS data-science transition | Combine cloud foundations with an end-to-end SageMaker workflow |
| Machine learning from scratch | Avoid elementary mathematics and library-only implementations |
| Python RAG application | Distinguish a real retrieval pipeline from a generic chatbot |

All five scenarios ran through the same code. Only the input JSON changed.

## Results

| Persona | Budget | Videos | Duration | Utilization | Technical | Adequacy | Evidence | Uncovered / unverified |
|---|---:|---:|---:|---:|---|---|---|---:|
| Weekend React developer | 360m | 5 | 309m 36s | 86.0% | PASS | NEEDS REVISION | LIMITED | 5 |
| Python data-science beginner | 420m | 4 | 358m 30s | 85.4% | PASS | NEEDS REVISION | LIMITED | 8 |
| AWS data-science transition | 480m | 6 | 344m 58s | 71.9% | PASS | NEEDS REVISION | LIMITED | 10 |
| Machine learning from scratch | 480m | 6 | 343m 17s | 71.5% | PASS | NEEDS REVISION | LIMITED | 8 |
| Python RAG application | 420m | 6 | 297m 15s | 70.8% | PASS | NEEDS REVISION | LIMITED | 7 |

Average budget utilization was approximately **77.1%**.

All five curricula:

- passed deterministic technical validation;
- stayed inside their hard budgets;
- selected between 4 and 6 videos;
- used at least 70% of the available learning time;
- relied on metadata because transcript retrieval was blocked;
- retained some uncovered or unverified areas.

## Human review of the results

### React

The strongest React baseline closely matches the reference output: five videos
and approximately 5 hours 10 minutes. It is project-oriented and avoids generic
JavaScript introductions. Its remaining warnings mostly reflect content that
cannot be verified from metadata.

### Python data science

The curriculum combines notebook orientation, a substantial data-analysis
course, a CSV project, and focused pandas practice. Main uncertainties are the
depth of Python fundamentals, exact cleaning operations, Colab-to-Jupyter
transfer, debugging, and reproducibility.

### AWS data science

An early run produced only about 115 minutes and lacked a substantial
foundation. The evaluator correctly flagged that result. The preserved
baseline improves to approximately 345 minutes and combines SageMaker
foundation, IAM/S3, CLI, boto3, an end-to-end project, and custom training.

### Machine learning from scratch

The curriculum correctly emphasizes mathematical implementations and NumPy
rather than scikit-learn-only instruction. It contains useful comparisons
between gradient-descent and closed-form regression, but also has meaningful
regression-topic redundancy. Numerical debugging, leakage-safe preprocessing,
metrics, reusable model APIs, and explicit scikit-learn comparison remain
unverified.

### Python RAG

The curriculum covers RAG architecture, chunking, embeddings, vector search,
and document question answering rather than returning a generic chatbot
tutorial. Its main weaknesses are framework dependence, overlap between project
videos, and no verified coverage of citations, retrieval evaluation, top-k
configuration, debugging, or end-to-end testing.

## Where automated evaluation and human judgment disagree

### Uncovered versus unverified

The current flag combines topics that are genuinely absent with topics that may
exist inside a video but cannot be confirmed from metadata. Consequently,
`NEEDS REVISION` often means "useful, but not fully verifiable" rather than
"bad curriculum."

### Backbone false negatives

The machine-learning and RAG curricula received backbone warnings even though
human review found plausible foundation and project resources. The title-and-role
heuristic cannot fully interpret pedagogical relationships.

### Short videos

A short video is not automatically superficial. A focused CLI, deployment,
boto3, or chunking supplement can be appropriate even when a learner rejects
surface-level introductions.

### Redundancy

Title similarity does not prove content duplication. Gradient-descent and
closed-form regression cover the same model but teach distinct approaches.
Conversely, differently titled videos may still repeat the same material.

### Duration

Budget utilization helped expose weak candidate pools, but duration is not a
direct quality measure. The evaluator does not treat low utilization as a hard
failure because padding would reduce curriculum quality.

## Failure cases and lessons

- **Transcript blocking:** `youtube-transcript-api` returned `RequestBlocked`
  in Codespaces, and yt-dlp subtitle retrieval encountered bot verification.
  The final system records the error and falls back to metadata.
- **Incomplete model assessments:** early calls sometimes omitted candidates.
  Smaller batches, candidate numbers, exact accounting, and duplicate checks
  made this failure explicit.
- **Weak candidate pools:** the first AWS run showed that selection cannot
  compensate for poor discovery.
- **Over-engineering:** additional retry, pool-quality, cache, and export
  scripts increased complexity without solving the evidence limitation. The
  final architecture was simplified.

## Signals considered but not used

- **Comments:** potentially useful for outdated code and missing steps, but
  noisy and unavailable without additional API access.
- **Community recommendations:** useful independent evidence, but require
  provenance, trust, ranking, and cross-source deduplication.
- **Views and likes:** popularity does not establish learner fit.
- **Descriptions and chapters:** valuable intermediate evidence, but not added
  in the final implementation.
- **Channel authority:** useful as a prior, but domain-dependent and weaker than
  direct content evidence.
- **External course platforms:** potentially better structured, but outside the
  requested YouTube curriculum scope.

## What this evaluation does not measure

It cannot determine:

- instructor clarity or pacing;
- whether the code currently runs;
- whether the learner completes or reproduces the project;
- true content-level duplication;
- whether a long video uses its time effectively;
- whether the sequence causes measurable learning gains;
- whether a selected video remains available.

The current evaluator measures structural validity and evidence-aware
plausibility, not actual educational outcomes.

## What I would evaluate next

1. Add descriptions and chapters before title-only fallback.
2. Create a small human-reviewed gold set.
3. Run blind pairwise curriculum comparisons.
4. Add content-level deduplication.
5. Separate discovery failures from selection failures.
6. Conduct learner outcome studies.
7. Instrument cost and latency before estimating scale.

## Conclusion

The system produces structurally valid, personalized, project-oriented
curricula across five distinct scenarios without code changes between personas.
Its principal limitation is evidence access rather than structural correctness.

The evaluation therefore distinguishes:

- what is mechanically correct;
- what is pedagogically plausible;
- what remains uncertain;
- where human judgment disagrees;
- which improvements would most increase confidence.
