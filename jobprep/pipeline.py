"""Day 30: integrate everything. text -> candidate + job -> gap -> advice."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from . import llm
from .config import DEFAULT, Config
from .extract import extract_resume, read_text
from .gap import analyze_gap
from .jd import parse_job
from .recommend import build_plan, build_questions


def analyze_text(resume_text: str, job_text: str, cfg: Config = DEFAULT, mode: str = "rules",
                 model: str | None = None, today: date | None = None, client=None) -> dict:
    """mode: 'rules' (offline, deterministic), 'llm' (Claude rewrites the advice), 'auto'."""
    if not resume_text.strip():
        raise ValueError("The resume is empty.")
    if not job_text.strip():
        raise ValueError("The job description is empty.")
    candidate = extract_resume(resume_text, cfg, today)
    job = parse_job(job_text, cfg)
    gap = analyze_gap(candidate, job, cfg)
    plan = build_plan(gap, candidate)
    questions = build_questions(gap, candidate)

    if mode == "auto":
        mode = "llm" if os.environ.get("ANTHROPIC_API_KEY") else "rules"
    warnings = list(candidate["warnings"]) + list(job["warnings"])
    used = "rules"
    if mode == "llm" and client is None and not os.environ.get("ANTHROPIC_API_KEY"):
        warnings.append("LLM mode needs ANTHROPIC_API_KEY. It is not set, so the offline rules engine was used.")
        mode = "rules"
    if mode == "llm":
        try:
            advice = llm.call_claude(llm.build_input(gap, candidate, job), model or llm.DEFAULT_MODEL, client)
        except Exception as e:      # network, auth or model error: keep the rule-based advice
            warnings.append(f"Claude call failed ({type(e).__name__}: {e}). The offline rules engine was used.")
        else:
            plan, questions, w = llm.validate(advice, gap, plan, questions)
            warnings += w
            used = "llm"

    return {"mode": used, "candidate": candidate, "job": job, "gap": gap, "plan": plan,
            "questions": questions, "warnings": warnings}


def analyze_files(resume_path: str | Path, job_path: str | Path, **kw) -> dict:
    return analyze_text(read_text(resume_path), read_text(job_path), **kw)
