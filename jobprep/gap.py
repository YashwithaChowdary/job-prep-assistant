"""Day 28: compare candidate skills with job requirements.

Each job skill ends up as one of:
  matched - the resume shows it (or implies it) at full level
  partial - the resume shows it only as basic / learning, or shows a close
            substitute (AWS for Azure). Worth half credit.
  missing - not on the resume (or the candidate says they have no experience)
"""
from __future__ import annotations

from .config import CREDIT, DEFAULT, FIT_MODERATE, FIT_STRONG, WEIGHT, Config
from .skills_kb import related_of


def analyze_gap(candidate: dict, job: dict, cfg: Config = DEFAULT) -> dict:
    cskills = candidate["skills"]
    items = []
    for tier in ("required", "preferred"):
        for skill in job[tier]:
            items.append(_assess(skill, tier, cskills, candidate, cfg))

    total = sum(i["weight"] for i in items)
    score = round(100 * sum(i["weight"] * i["credit"] for i in items) / total, 1) if total else None
    fit = None if score is None else ("strong" if score >= FIT_STRONG else "moderate" if score >= FIT_MODERATE else "weak")

    req = [i for i in items if i["tier"] == "required"]
    gap = {
        "score": score,
        "fit": fit,
        "items": items,
        "counts": {s: sum(i["status"] == s for i in items) for s in ("matched", "partial", "missing")},
        "required_counts": {s: sum(i["status"] == s for i in req) for s in ("matched", "partial", "missing")},
        "experience": _experience_note(candidate.get("years_experience"), job.get("min_years")),
    }
    gap["summary"] = _summary(gap, job, candidate)
    return gap


def _assess(skill: str, tier: str, cskills: dict, candidate: dict, cfg: Config) -> dict:
    item = {"skill": skill, "tier": tier, "weight": WEIGHT[tier], "status": "missing", "credit": 0.0,
            "reason": "", "evidence": None, "strength": None, "related_held": [], "listed_only": False}
    rec = cskills.get(skill)
    if rec:
        item["strength"] = rec["strength"]
        item["evidence"] = rec["evidence"][0]["text"] if rec["evidence"] else None
        if rec["level"] == "full":
            item["status"] = "matched"
            if rec["strength"] == "implied":
                item["reason"] = f"Not stated directly, but implied by {', '.join(rec['implied_by'])}."
            else:
                where = rec["evidence"][0]["section"]
                item["reason"] = f"Found in the {where} section."
            item["listed_only"] = rec["strength"] == "listed"
            if item["listed_only"]:
                item["reason"] += " Listed only: no job or project evidence, so be ready to prove it."
        else:
            item["status"] = "partial"
            item["reason"] = "Mentioned as basic or still being learned."
    elif skill in candidate.get("negated_skills", []):
        item["reason"] = "The resume says the candidate has no experience with it."
    else:
        item["reason"] = "Not found on the resume."

    if item["status"] == "missing" and cfg.use_related:
        held = [r for r in related_of(skill) if cskills.get(r, {}).get("level") == "full"]
        if held:
            item["status"] = "partial"
            item["related_held"] = held
            item["reason"] = f"Not on the resume, but the candidate has a close substitute: {', '.join(held)}."
    item["credit"] = CREDIT[item["status"]]
    return item


def _experience_note(have: float | None, need: int | None) -> dict:
    if need is None:
        return {"status": "not_required", "text": "The job description does not state years of experience."}
    if have is None:
        return {"status": "unknown", "text": f"The role asks for {need}+ years; the resume has no readable dates."}
    if have >= need:
        return {"status": "meets",
                "text": f"{have} years found vs {need}+ asked. Note: this counts ALL experience, not only relevant experience."}
    return {"status": "below", "text": f"{have} years found vs {need}+ asked."}


def _summary(gap: dict, job: dict, candidate: dict) -> str:
    if gap["score"] is None:
        return "No known skills were found in the job description, so no match could be computed."
    rc, items = gap["required_counts"], gap["items"]
    n_req = sum(rc.values())
    parts = [f"{gap['score']}% match ({gap['fit']} fit) for '{job['title']}'."]
    if n_req:
        parts.append(f"Required skills: {rc['matched']} of {n_req} fully matched, {rc['partial']} partial, {rc['missing']} missing.")
    missing = [i["skill"] for i in items if i["tier"] == "required" and i["status"] == "missing"]
    if missing:
        parts.append("Biggest gaps: " + ", ".join(missing[:4]) + ".")
    strong = [i["skill"] for i in items if i["tier"] == "required" and i["status"] == "matched" and not i["listed_only"]]
    if strong:
        parts.append("Strongest evidence: " + ", ".join(strong[:4]) + ".")
    return " ".join(parts)
