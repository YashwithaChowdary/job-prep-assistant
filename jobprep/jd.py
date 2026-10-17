"""Day 27: turn a job description into required / preferred skills.

Section headings decide the tier ("Requirements" vs "Nice to have"), a cue in
the line itself ("is a plus", "preferred") overrides the section, and
"About us" text is ignored so a mention of the company's own stack does not
become a requirement.
"""
from __future__ import annotations

import re

from .config import DEFAULT, Config
from .extract import _clip, redact_pii
from .matcher import find_mentions

_HEADS = {
    "required": {"requirements", "required", "required skills", "must have", "musthaves", "qualifications",
                 "minimum qualifications", "what you bring", "what were looking for", "you have", "you will need",
                 "required qualifications", "skills required", "responsibilities", "what youll do", "duties",
                 "the role", "role", "about the role"},
    "preferred": {"preferred", "preferred qualifications", "preferred skills", "nice to have", "nicetohaves",
                  "bonus", "bonus points", "plus", "good to have", "desirable"},
    "context": {"about us", "about the company", "who we are", "company", "benefits", "perks", "what we offer"},
}
_HEAD_LOOKUP = {h: t for t, hs in _HEADS.items() for h in hs}
_PREF_CUE = re.compile(r"\b(nice to have|preferred|a plus|is a plus|are a plus|bonus|good to have|ideally|desirable|advantage|helpful|not essential|not required)\b", re.I)
_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:years|yrs)", re.I)
_DEGREE = re.compile(r"\b(bachelor\w*|b\.?\s?tech|master\w*|m\.?\s?tech|ph\.?d|degree)\b", re.I)


def _heading(line: str) -> str | None:
    s = line.strip().rstrip(":").strip()
    if not s or len(s) > 50 or s.endswith("."):
        return None
    key = re.sub(r"[^a-z ]", "", s.lower().replace("'", "")).strip()
    return _HEAD_LOOKUP.get(key)


def parse_job(text: str, cfg: Config = DEFAULT) -> dict:
    text = redact_pii(text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title = _clip(lines[0], 80) if lines else "Unknown role"

    tier_of: dict[str, str] = {}
    evidence: dict[str, str] = {}
    ignored: set[str] = set()
    section = "required"      # a flat job description counts as all-required
    min_years, degree = None, None

    for line in lines[1:]:
        head = _heading(line) if cfg.use_jd_sections else None
        if head:
            section = head
            continue
        if min_years is None and section != "preferred":
            ym = _YEARS.search(line)
            if ym and re.search(r"experience|work|industry|role", line, re.I):
                min_years = int(ym.group(1))
        if degree is None and section != "preferred" and _DEGREE.search(line):
            degree = _clip(line, 100)
        # cues work per sentence, so one prose paragraph can hold both tiers
        for sent in re.split(r"(?<=[.!?])\s+", line):
            tier = section
            if cfg.use_jd_sections and _PREF_CUE.search(sent):
                tier = "preferred"
            for m in find_mentions(sent, cfg, with_cues=False):
                if tier == "context":
                    ignored.add(m.skill)
                    continue
                if tier_of.get(m.skill) != "required":      # required beats preferred
                    tier_of[m.skill] = tier
                    evidence[m.skill] = _clip(sent, 100)

    ignored -= set(tier_of)
    return {
        "title": title,
        "required": [s for s, t in tier_of.items() if t == "required"],
        "preferred": [s for s, t in tier_of.items() if t == "preferred"],
        "ignored_context_skills": sorted(ignored),
        "evidence": evidence,
        "min_years": min_years,
        "degree_requirement": degree,
        "warnings": [] if tier_of else ["No known skills found in the job description."],
    }
