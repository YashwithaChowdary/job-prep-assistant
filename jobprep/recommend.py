"""Day 29: learning plan and interview questions, each with an explanation.

Rule-based and deterministic. The optional Claude layer (llm.py) can rewrite
them, but it is validated against the same facts.
"""
from __future__ import annotations

import math

from .skills_kb import KB

MAX_PLAN_ITEMS = 6


def build_plan(gap: dict, candidate: dict) -> dict:
    held = {s for s, r in candidate["skills"].items() if r["level"] == "full"}
    targets = [i for i in gap["items"] if i["status"] in ("missing", "partial")]
    # biggest remaining value first (weight x missing credit), quick wins break ties
    targets.sort(key=lambda i: (-(i["weight"] * (1 - i["credit"])), KB[i["skill"]].weeks))
    steps, week = [], 1
    for i in targets[:MAX_PLAN_ITEMS]:
        kb = KB[i["skill"]]
        have_prereq = [p for p in kb.builds_on if p in held]
        factor = 1.0
        notes = []
        if i["status"] == "partial":
            factor *= 0.6
            notes.append("you already have a start (basic knowledge or a close substitute)")
        if have_prereq:
            factor *= max(0.55, 1 - 0.15 * len(have_prereq))
            notes.append(f"you already know {', '.join(have_prereq)}, which it builds on")
        weeks = max(1, math.ceil(kb.weeks * factor))
        why = (f"{'Required' if i['tier'] == 'required' else 'Preferred'} for this role, and "
               f"{i['reason'][0].lower() + i['reason'][1:]}")
        if notes:
            why += " Estimated time is shorter because " + " and ".join(notes) + "."
        steps.append({
            "priority": len(steps) + 1, "skill": i["skill"], "tier": i["tier"], "status": i["status"],
            "weeks": weeks, "start_week": week, "end_week": week + weeks - 1,
            "topics": list(kb.topics), "practice_project": kb.project, "explanation": why,
        })
        week += weeks
    skipped = [i["skill"] for i in targets[MAX_PLAN_ITEMS:]]
    strengths = [i["skill"] for i in gap["items"]
                 if i["tier"] == "required" and i["status"] == "matched" and not i["listed_only"]]
    return {"steps": steps, "total_weeks": week - 1 if steps else 0, "not_in_plan": skipped,
            "emphasise_on_resume": strengths[:5],
            "note": "Week estimates are rough, for about 10 hours of study per week."}


def build_questions(gap: dict, candidate: dict, limit: int = 12) -> list[dict]:
    qs: list[dict] = []
    items = gap["items"]
    # 1) skills the candidate claims: probe them on their own evidence
    claimed = [i for i in items if i["status"] == "matched" and i["strength"] != "implied"]
    claimed.sort(key=lambda i: (i["tier"] != "required", i["strength"] != "demonstrated"))
    for i in claimed[:4]:
        if i["listed_only"]:
            q = (f"You list {i['skill']} but we see no project or job using it. "
                 f"Describe the most complex thing you have built with it.")
            why = "Skills listed without evidence are the first thing interviewers test."
        else:
            q = (f"Your resume says: \"{i['evidence']}\". What was your own contribution, "
                 f"and what would you do differently now?")
            why = f"{i['skill']} is {i['tier']} for the role and you have evidence for it, so expect depth questions."
        qs.append({"type": "resume-probe", "skill": i["skill"], "question": q, "why": why})
        qs.append({"type": "technical", "skill": i["skill"], "question": KB[i["skill"]].questions[0],
                   "why": f"A standard check of {i['skill']} fundamentals."})
    # 2) gaps in required skills: be ready to answer honestly
    gaps = [i for i in items if i["status"] in ("missing", "partial") and i["tier"] == "required"]
    for i in gaps[:3]:
        q = KB[i["skill"]].questions[-1]
        qs.append({"type": "gap", "skill": i["skill"], "question": q,
                   "why": f"{i['skill']} is required and {'only partly shown' if i['status'] == 'partial' else 'not shown'} on "
                          f"your resume. Prepare an honest answer and a plan for how you would ramp up."})
    # 3) behavioural, from the candidate's own projects
    for p in candidate.get("projects", [])[:2]:
        qs.append({"type": "behavioural", "skill": None,
                   "question": f"Walk me through '{p['title']}': what problem it solved, the trade-offs you made, and what went wrong.",
                   "why": "Project walk-throughs show whether the work is really yours."})
    if gaps:
        qs.append({"type": "behavioural", "skill": None,
                   "question": "Tell me about a time you had to learn a new technology quickly. How did you do it?",
                   "why": "You have skill gaps, so expect questions about how fast you learn."})
    return qs[:limit]
