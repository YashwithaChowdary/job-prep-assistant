"""Day 30: test on several resume / job pairs and score against hand labels.

Metrics (all micro-averaged over the labelled cases):
  resume_f1   skills found on the resume vs skills actually stated (implied skills excluded)
  jd_f1       (skill, tier) pairs found in the job description vs labelled
  gap_acc     status (matched / partial / missing) per job skill vs labelled
  fit_acc     overall fit band (strong / moderate / weak) vs labelled
Evaluation runs in 'rules' mode: it is deterministic and needs no API key.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .config import DEFAULT, Config
from .extract import read_text
from .pipeline import analyze_text

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
EVAL_DATE = date(2026, 10, 17)      # fixed so "Present" in a resume never changes the result


def load_cases(samples: Path = SAMPLES) -> list[dict]:
    return json.loads((samples / "labels.json").read_text())["cases"]


def _prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3)}


def run_case(case: dict, cfg: Config = DEFAULT, samples: Path = SAMPLES) -> dict:
    result = analyze_text(read_text(samples / case["resume"]), read_text(samples / case["job"]),
                          cfg, mode="rules", today=EVAL_DATE)
    found = {s for s, v in result["candidate"]["skills"].items() if v["strength"] != "implied"}
    truth = set(case["resume_skills"])
    jd_pred = {(s, "required") for s in result["job"]["required"]} | {(s, "preferred") for s in result["job"]["preferred"]}
    jd_true = {(s, "required") for s in case["jd_required"]} | {(s, "preferred") for s in case["jd_preferred"]}
    status = {i["skill"]: i["status"] for i in result["gap"]["items"]}
    gap_ok = {s: status.get(s) == exp for s, exp in case["expected_gap"].items()}
    return {
        "id": case["id"], "result": result,
        "resume": {"tp": len(found & truth), "fp": sorted(found - truth), "fn": sorted(truth - found)},
        "jd": {"tp": len(jd_pred & jd_true), "fp": sorted(jd_pred - jd_true), "fn": sorted(jd_true - jd_pred)},
        "gap": {"correct": sum(gap_ok.values()), "total": len(gap_ok),
                "wrong": {s: {"expected": case["expected_gap"][s], "got": status.get(s)} for s, ok in gap_ok.items() if not ok}},
        "fit": {"expected": case["expected_fit"], "got": result["gap"]["fit"], "score": result["gap"]["score"],
                "ok": result["gap"]["fit"] == case["expected_fit"]},
    }


def evaluate(cfg: Config = DEFAULT, samples: Path = SAMPLES) -> dict:
    runs = [run_case(c, cfg, samples) for c in load_cases(samples)]
    r_tp = sum(r["resume"]["tp"] for r in runs)
    r_fp = sum(len(r["resume"]["fp"]) for r in runs)
    r_fn = sum(len(r["resume"]["fn"]) for r in runs)
    j_tp = sum(r["jd"]["tp"] for r in runs)
    j_fp = sum(len(r["jd"]["fp"]) for r in runs)
    j_fn = sum(len(r["jd"]["fn"]) for r in runs)
    g_ok = sum(r["gap"]["correct"] for r in runs)
    g_all = sum(r["gap"]["total"] for r in runs)
    return {
        "resume_skills": _prf(r_tp, r_fp, r_fn),
        "job_skills": _prf(j_tp, j_fp, j_fn),
        "gap_accuracy": round(g_ok / g_all, 3),
        "fit_accuracy": round(sum(r["fit"]["ok"] for r in runs) / len(runs), 3),
        "cases": runs,
    }
