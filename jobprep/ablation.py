"""Switch off one feature at a time and measure what the evaluation loses."""
from __future__ import annotations

from .config import DEFAULT
from .evaluate import evaluate

VARIANTS = {
    "full system": {},
    "no aliases": {"use_aliases": False},
    "no implied skills": {"use_implied": False},
    "no related-skill credit": {"use_related": False},
    "no JD sections": {"use_jd_sections": False},
    "no negation / partial cues": {"use_negation": False},
}


def run_ablation() -> list[dict]:
    rows = []
    for name, flags in VARIANTS.items():
        ev = evaluate(DEFAULT.without(**flags) if flags else DEFAULT)
        rows.append({"variant": name, "resume_f1": ev["resume_skills"]["f1"], "job_f1": ev["job_skills"]["f1"],
                     "gap_accuracy": ev["gap_accuracy"], "fit_accuracy": ev["fit_accuracy"]})
    return rows


def to_markdown(rows: list[dict]) -> str:
    base = rows[0]
    L = ["| Variant | Resume F1 | Job F1 | Gap accuracy | Fit accuracy | Gap change |", "|---|---|---|---|---|---|"]
    for r in rows:
        d = r["gap_accuracy"] - base["gap_accuracy"]
        L.append(f"| {r['variant']} | {r['resume_f1']} | {r['job_f1']} | {r['gap_accuracy']} | {r['fit_accuracy']} | {d:+.3f} |")
    return "\n".join(L) + "\n"
