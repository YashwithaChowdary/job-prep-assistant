# Failures found and limitations

## Stress cases found bugs (cases 07-09, written after the first six passed)

The first six samples scored 1.0 on every metric. Because I designed them, that proves little, so I wrote three harder cases and ran them untouched.

| Metric | First run on all 9 | After fixes |
|---|---|---|
| Resume skill F1 | 0.977 | 0.994 |
| Job skill F1 | 0.958 | 1.000 |
| Gap accuracy | 0.972 | 0.986 |
| Fit band accuracy | 1.000 | 1.000 |

| Failure | Cause | Fix |
|---|---|---|
| "Shell Energy" read as the skill Bash | alias "Shell" too generic | removed it; "shell scripting" kept |
| "Spring 2025" read as Spring Boot | alias "Spring" too generic | replaced by "Spring Framework" |
| "TF" not recognised as TensorFlow | missing alias | added (case-sensitive) |
| Prose job description: every skill became "preferred" | the "is a plus" cue was applied to the whole line | cues are now applied per sentence |
| "no hands-on Kubernetes administration" counted as a claim | negation list lacked "no hands-on" | added |

## Still failing (not fixed on purpose)

- Case 07, Kubernetes: the line says "Ran workloads on nodes of a Kubernetes cluster ... (no hands-on Kubernetes administration)". The first mention has no negation before it, so it counts as used. A human could argue either way. Fixing it would mean letting a later negation override an earlier mention, which risks hiding real skills, so it stays documented.

## Limitations

- About 64 skills are known. Others are listed as "not scored", never silently dropped.
- Ambiguous names (R, Go) are excluded to avoid false matches.
- Years of experience count all roles, not relevant ones (visible in case 05).
- A negation or "learning" cue only reaches back to the previous comma, semicolon or full stop.
- Scanned PDFs are not supported (no OCR).
- LLM mode is tested with a fake client and guard-rail tests, not live: no API key was available.
- Week estimates in the learning plan are rough.
- Nine hand-labelled synthetic pairs written by one person is a small test. Scores show the code does what I intended, not how it would do on real resumes.
