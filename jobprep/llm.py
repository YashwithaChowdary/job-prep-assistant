"""Optional Claude layer: rewrites the learning plan and interview questions
so they read as personal advice.

Safety rules (same idea as the Week 5 project: code finds facts, AI explains):
  - Claude never sees the resume text. It receives the structured gap result
    (skill names, statuses, project titles). Personal data was already redacted.
  - It answers through a forced tool call with a JSON schema.
  - Its output is validated: a plan item must target a skill that is really
    missing or partial, a question must target a skill from the job description,
    and anything else is dropped and replaced by the rule-based version.
"""
from __future__ import annotations

import json
import os

DEFAULT_MODEL = os.environ.get("JOBPREP_MODEL", "claude-sonnet-5-5")

TOOL = {
    "name": "submit_advice",
    "description": "Submit the personalised learning plan and interview questions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "plan": {"type": "array", "items": {"type": "object", "properties": {
                "skill": {"type": "string"},
                "weeks": {"type": "integer"},
                "steps": {"type": "array", "items": {"type": "string"}},
                "practice_project": {"type": "string"},
                "explanation": {"type": "string"}},
                "required": ["skill", "weeks", "steps", "practice_project", "explanation"]}},
            "questions": {"type": "array", "items": {"type": "object", "properties": {
                "skill": {"type": "string", "description": "A skill from the job description, or 'behavioural'"},
                "question": {"type": "string"},
                "explanation": {"type": "string"}},
                "required": ["skill", "question", "explanation"]}},
        },
        "required": ["plan", "questions"],
    },
}

SYSTEM = """You are a careful career coach. You receive a structured skill-gap analysis for one \
candidate and one job. Write a learning plan and interview questions.

Rules:
- Only plan for skills whose status is missing or partial. Do not invent other gaps.
- Only ask about skills that appear in the job description (or use 'behavioural').
- Never claim the candidate has experience that the analysis does not show.
- Be concrete: name topics to study and one small project that proves the skill.
- Each plan item and each question needs a short explanation of why it was chosen."""


def build_input(gap: dict, candidate: dict, job: dict) -> dict:
    return {
        "job_title": job["title"],
        "fit": gap["fit"], "score": gap["score"],
        "skills": [{"skill": i["skill"], "tier": i["tier"], "status": i["status"],
                    "held_substitutes": i["related_held"], "listed_only": i["listed_only"]}
                   for i in gap["items"]],
        "project_titles": [p["title"] for p in candidate.get("projects", [])][:4],
        "years_experience": candidate.get("years_experience"),
    }


def call_claude(payload: dict, model: str = DEFAULT_MODEL, client=None) -> dict:
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model, max_tokens=3000, system=SYSTEM, tools=[TOOL],
        tool_choice={"type": "tool", "name": "submit_advice"},
        messages=[{"role": "user", "content": "Analysis:\n```json\n" + json.dumps(payload, indent=1) + "\n```"}])
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    raise RuntimeError("Model did not return a tool_use block")


def validate(advice: dict, gap: dict, rule_plan: dict, rule_questions: list[dict]) -> tuple[dict, list[dict], list[str]]:
    """Drop anything the facts do not support; fall back to the rule-based version if nothing survives."""
    warnings: list[str] = []
    status = {i["skill"]: i["status"] for i in gap["items"]}
    rule_by_skill = {s["skill"]: s for s in rule_plan["steps"]}

    steps = []
    for item in advice.get("plan", []):
        sk = item.get("skill")
        if status.get(sk) not in ("missing", "partial"):
            warnings.append(f"Dropped plan item for '{sk}': it is not a missing or partial skill for this job.")
            continue
        weeks = min(12, max(1, int(item.get("weeks", 1) or 1)))
        base = rule_by_skill.get(sk, {})
        steps.append({"skill": sk, "tier": next(i["tier"] for i in gap["items"] if i["skill"] == sk),
                      "status": status[sk], "weeks": weeks, "topics": list(item.get("steps", []))[:5],
                      "practice_project": item.get("practice_project") or base.get("practice_project", ""),
                      "explanation": item.get("explanation", "")})
    plan = dict(rule_plan)
    if steps:
        week = 1
        for n, s in enumerate(steps, 1):
            s.update(priority=n, start_week=week, end_week=week + s["weeks"] - 1)
            week += s["weeks"]
        plan.update(steps=steps, total_weeks=week - 1)
    else:
        warnings.append("No valid plan items from the model; using the rule-based plan.")

    questions = []
    for q in advice.get("questions", []):
        sk = q.get("skill")
        if sk not in status and sk != "behavioural":
            warnings.append(f"Dropped question about '{sk}': not a skill in the job description.")
            continue
        questions.append({"type": "ai", "skill": None if sk == "behavioural" else sk,
                          "question": q.get("question", ""), "why": q.get("explanation", "")})
    if not questions:
        warnings.append("No valid questions from the model; using the rule-based questions.")
        questions = rule_questions
    return plan, questions, warnings
