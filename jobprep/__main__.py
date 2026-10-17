"""Command line: python -m jobprep <demo|analyze|evaluate|ablation>"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import analyze_files
from .report import to_html, to_markdown


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="jobprep", description="AI-Powered Job Preparation Assistant")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="analyse one resume against one job description")
    a.add_argument("resume"); a.add_argument("job")
    a.add_argument("--mode", choices=["rules", "llm", "auto"], default="rules")
    a.add_argument("--out", help="folder to write report.md / report.html / report.json")
    d = sub.add_parser("demo", help="run the built-in sample pair")
    d.add_argument("--case", default="01", help="sample number 01-09")
    sub.add_parser("evaluate", help="score the extractor against the hand labels")
    sub.add_parser("ablation", help="turn features off one at a time")
    args = ap.parse_args(argv)

    if args.cmd in ("analyze", "demo"):
        if args.cmd == "demo":
            from .evaluate import SAMPLES, load_cases
            case = next((c for c in load_cases() if c["id"].startswith(args.case)), None)
            if not case:
                print(f"No sample starting with '{args.case}'."); return 2
            args.resume, args.job, args.mode, args.out = SAMPLES / case["resume"], SAMPLES / case["job"], "rules", None
        try:
            r = analyze_files(args.resume, args.job, mode=args.mode)
        except (ValueError, FileNotFoundError, RuntimeError) as e:
            print(f"Error: {e}", file=sys.stderr); return 1
        print(to_markdown(r))
        if args.out:
            out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
            (out / "report.md").write_text(to_markdown(r)); (out / "report.html").write_text(to_html(r))
            (out / "report.json").write_text(json.dumps(r, indent=2, default=str))
            print(f"Saved to {out}/")
    elif args.cmd == "evaluate":
        from .evaluate import evaluate
        ev = evaluate()
        print("Resume skills :", ev["resume_skills"]); print("Job skills    :", ev["job_skills"])
        print("Gap accuracy  :", ev["gap_accuracy"]); print("Fit accuracy  :", ev["fit_accuracy"], "\n")
        for c in ev["cases"]:
            print(f"{'OK ' if c['fit']['ok'] else 'BAD'} {c['id']:36} {c['fit']['got']:8} {c['fit']['score']}")
    else:
        from .ablation import run_ablation, to_markdown as md
        print(md(run_ablation()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
