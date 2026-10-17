"""Find skill mentions in a line of text.

Handles: aliases, longest-match-first (so "Azure DevOps" is not also "Azure"),
word boundaries that respect C++ / C# / Node.js, and simple cues in the same
clause such as "no experience with X" (negated) or "currently learning X" /
"X (basic)" (partial).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from .config import Config
from .skills_kb import KB

_NEG = re.compile(
    r"\b(no|not|never|without|lack(?:ing)?)\b\s+(?:\w+\s+){0,2}?(experience|knowledge|exposure|familiarity|used|worked)\b"
    r"|\bnot\s+familiar\b|\bno\s+hands-?on\b", re.I)
_PART_PRE = re.compile(
    r"\b(currently|still|now)\s+learning\b|\blearning\s+to\b|\bstudying\b|\bbasics?\b|\bbeginner\b|\bnovice\b"
    r"|\bexposure\s+to\b|\b(?:want|plan(?:ning)?|intend)\s+to\s+learn\b", re.I)
_PART_POST = re.compile(r"^\s*[\(\[\-–:]\s*(basic|beginner|learning|novice|elementary)\b", re.I)
_CLAUSE_END = re.compile(r"[,;.!?\n]")


@dataclass(frozen=True)
class Mention:
    skill: str
    start: int
    end: int
    level: str      # "full" | "partial" | "negated"


@lru_cache(maxsize=4)
def _patterns(use_aliases: bool) -> tuple[tuple[re.Pattern, str], ...]:
    entries: list[tuple[str, str]] = []
    for s in KB.values():
        names = [s.name, *(s.aliases if use_aliases else ())]
        entries += [(n, s.name) for n in names]
    entries.sort(key=lambda e: -len(e[0]))            # longest first
    out = []
    for text, skill in entries:
        flags = 0 if (len(text) <= 3 and text.isupper()) else re.I   # "ML", "AWS" are case-sensitive
        pat = re.compile(r"(?<![A-Za-z0-9+#])" + re.escape(text) + r"(?![A-Za-z0-9+#])", flags)
        out.append((pat, skill))
    return tuple(out)


def find_mentions(line: str, cfg: Config, with_cues: bool = True) -> list[Mention]:
    taken: list[tuple[int, int]] = []
    found: list[Mention] = []
    for pat, skill in _patterns(cfg.use_aliases):
        for m in pat.finditer(line):
            s, e = m.span()
            if any(s < te and e > ts for ts, te in taken):
                continue
            taken.append((s, e))
            found.append(Mention(skill, s, e, _level(line, s, e) if (with_cues and cfg.use_negation) else "full"))
    return sorted(found, key=lambda x: x.start)


def _level(line: str, start: int, end: int) -> str:
    cut = 0
    for m in _CLAUSE_END.finditer(line, 0, start):
        cut = m.end()
    pre = line[cut:start]
    if _NEG.search(pre):
        return "negated"
    if _PART_PRE.search(pre) or _PART_POST.match(line[end:end + 16]):
        return "partial"
    return "full"
