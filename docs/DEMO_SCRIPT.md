# 5-minute demo script

**0:00 Problem.** Resumes and job posts do not tell you what to learn next. This tool compares them and explains the gap.

**0:30 Run it.** `streamlit run app.py`, pick sample 03 (Java developer applying for a GenAI role). Click Analyse.

**1:15 Skill gap tab.** 25% weak fit. Python and LLMs are Partial because the resume says "currently learning". RAG and Vector DBs are Missing because the resume says "no experience". Point out these were not counted as matches.

**2:15 Learning plan.** Ordered by impact; weeks shortened where prerequisites exist. Each step has study topics and a proof project.

**3:00 Interview questions.** Each has a "why this question".

**3:30 Trust.** Switch to sample 01: Python never appears on the resume, yet it is matched as implied by pandas and scikit-learn. Sample 04 is a PDF using "k8s" and "GH Actions".

**4:00 Evidence.** `python -m jobprep evaluate` (9 hand-labelled pairs) and `python -m jobprep ablation` (switching off aliases drops gap accuracy 15 points). Mention the stress cases that found 5 bugs and the one still failing.

**4:40 Limits and next step.** 64 skills, no OCR, small synthetic test set; production needs real resumes and a larger skills taxonomy.
