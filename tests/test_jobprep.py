from types import SimpleNamespace

import pytest

from jobprep import llm
from jobprep.ablation import run_ablation
from jobprep.config import DEFAULT
from jobprep.evaluate import SAMPLES, evaluate
from jobprep.extract import read_text, redact_pii
from jobprep.jd import parse_job
from jobprep.matcher import find_mentions
from jobprep.pipeline import analyze_text


def lv(text):
    return {m.skill: m.level for m in find_mentions(text, DEFAULT)}


def test_reads_txt_docx_pdf():
    for f, word in [("resume_01.txt", "pandas"), ("resume_03.docx", "Java"), ("resume_04.pdf", "Terraform")]:
        assert word.lower() in read_text(SAMPLES / f).lower()


def test_alias_and_boundaries():
    assert "Kubernetes" in lv("deployed on k8s")
    assert "TensorFlow" in lv("models in TF")
    assert "C++" in lv("wrote C++ code") and "Java" not in lv("wrote JavaScript")
    assert not lv("Shell Energy, Spring 2025")


def test_negation_and_partial():
    assert lv("no experience with Terraform")["Terraform"] == "negated"
    assert lv("currently learning Docker")["Docker"] == "partial"
    assert lv("Python (basic)")["Python"] == "partial"
    assert lv("no hands-on Kubernetes administration")["Kubernetes"] == "negated"


def test_pii_redacted():
    out = redact_pii("mail a@b.com or call +91 98765 43210 see https://x.io")
    assert "a@b.com" not in out and "98765" not in out and "https://x.io" not in out


def test_jd_sections_and_context():
    j = parse_job("Role\nAbout us\nWe run Kafka.\nRequirements\n- Python\nNice to have\n- Docker\n")
    assert j["required"] == ["Python"] and j["preferred"] == ["Docker"] and "Kafka" in j["ignored_context_skills"]


def test_prose_jd_cues_per_sentence():
    j = parse_job("Engineer\nYou will use AWS. Knowing Azure is a plus.")
    assert j["required"] == ["AWS"] and j["preferred"] == ["Azure"]


def test_implied_python():
    r = analyze_text(read_text(SAMPLES / "resume_01.txt"), "Role\nRequirements\n- Python\n")
    item = r["gap"]["items"][0]
    assert item["status"] == "matched" and item["strength"] == "implied"


def test_related_gets_partial_credit():
    r = analyze_text("Skills\nAWS", "Role\nRequirements\n- Azure\n")
    assert r["gap"]["items"][0]["status"] == "partial"


def test_empty_inputs():
    with pytest.raises(ValueError):
        analyze_text("", "x")
    with pytest.raises(ValueError):
        analyze_text("x", "  ")


def _fake(advice):
    block = SimpleNamespace(type="tool_use", input=advice)
    return SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: SimpleNamespace(content=[block])))


def test_llm_guardrails_drop_invented_items():
    advice = {"plan": [{"skill": "Rust", "weeks": 99, "steps": [], "practice_project": "x", "explanation": "x"},
                       {"skill": "Kubernetes", "weeks": 99, "steps": ["pods"], "practice_project": "p", "explanation": "e"}],
              "questions": [{"skill": "Rust", "question": "q", "explanation": "e"}]}
    r = analyze_text("Skills\nPython", "Role\nRequirements\n- Python\n- Kubernetes\n", mode="llm", client=_fake(advice))
    assert [s["skill"] for s in r["plan"]["steps"]] == ["Kubernetes"]
    assert r["plan"]["steps"][0]["weeks"] == 12
    assert all(q["skill"] != "Rust" for q in r["questions"]) and r["warnings"]


def test_evaluation_thresholds():
    ev = evaluate()
    assert ev["fit_accuracy"] == 1.0 and ev["gap_accuracy"] >= 0.95
    assert ev["resume_skills"]["f1"] >= 0.95 and ev["job_skills"]["f1"] >= 0.95


def test_ablation_each_feature_matters():
    rows = {r["variant"]: r for r in run_ablation()}
    base = rows["full system"]
    for name, r in rows.items():
        if name != "full system":
            assert (r["gap_accuracy"], r["fit_accuracy"], r["job_f1"], r["resume_f1"]) < (
                base["gap_accuracy"], base["fit_accuracy"], base["job_f1"], base["resume_f1"]) or r["fit_accuracy"] < 1 or r["job_f1"] < 1


def test_llm_mode_without_key_falls_back(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = analyze_text("Skills\nPython", "Role\nRequirements\n- Python\n", mode="llm")
    assert r["mode"] == "rules" and any("ANTHROPIC_API_KEY" in w for w in r["warnings"])


def test_llm_error_falls_back():
    class Boom:
        class messages:
            @staticmethod
            def create(**kw):
                raise ConnectionError("offline")
    r = analyze_text("Skills\nPython", "Role\nRequirements\n- Python\n", mode="llm", client=Boom())
    assert r["mode"] == "rules" and any("failed" in w for w in r["warnings"])
