"""Streamlit web app:  streamlit run app.py"""
import tempfile
from pathlib import Path

import streamlit as st

from jobprep.evaluate import SAMPLES, load_cases
from jobprep.extract import read_text
from jobprep.pipeline import analyze_text
from jobprep.report import ICON, LABEL, to_markdown

st.set_page_config(page_title="Job Preparation Assistant", layout="wide")
st.title("AI-Powered Job Preparation Assistant")
st.caption("Upload a resume and a job description. Facts come from code; advice can optionally be written by Claude.")

cases = load_cases()
with st.sidebar:
    st.header("Input")
    sample = st.selectbox("Try a sample pair", ["(none)"] + [c["id"] for c in cases])
    mode = st.radio("Advice engine", ["rules", "llm"], help="'llm' needs ANTHROPIC_API_KEY")

resume_text = job_text = ""
if sample != "(none)":
    c = next(c for c in cases if c["id"] == sample)
    resume_text, job_text = read_text(SAMPLES / c["resume"]), read_text(SAMPLES / c["job"])

col1, col2 = st.columns(2)
with col1:
    up = st.file_uploader("Resume (txt, docx, pdf)", type=["txt", "md", "docx", "pdf"])
    if up is not None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / up.name
            p.write_bytes(up.getvalue())
            try:
                resume_text = read_text(p)
            except ValueError as e:
                st.error(str(e))
    resume_text = st.text_area("Resume text", resume_text, height=300,
                               placeholder="Upload a resume above, paste it here, or pick a sample pair on the left.", key=f"r_{sample}_{up.name if up else ''}")
with col2:
    job_text = st.text_area("Job description", job_text, height=380, key=f"j_{sample}",
                            placeholder="Paste the job description here (title on the first line).")

if st.button("Analyse", type="primary"):
    missing = [n for n, t in (("a resume", resume_text), ("a job description", job_text)) if not t.strip()]
    if missing:
        st.info("Please add " + " and ".join(missing) + ", or pick a sample pair in the sidebar.")
        st.stop()
    try:
        r = analyze_text(resume_text, job_text, mode=mode)
    except Exception as e:  # show friendly message instead of a stack trace
        st.error(f"Could not analyse: {e}")
    else:
        g = r["gap"]
        st.metric("Match score", f"{g['score']}%", g["fit"] + " fit", delta_color="off", delta_arrow="off")
        st.write(g["summary"])
        for w in r["warnings"]:
            st.warning(w)
        t1, t2, t3, t4 = st.tabs(["Skill gap", "Learning plan", "Interview questions", "Resume profile"])
        with t1:
            st.dataframe([{"Skill": i["skill"], "Tier": i["tier"], "Status": f"{ICON[i['status']]} {LABEL[i['status']]}",
                        "Why": i["reason"]} for i in g["items"]], width='stretch', hide_index=True)
            st.caption(g["experience"]["text"])
        with t2:
            for s in r["plan"]["steps"]:
                with st.expander(f"{s['priority']}. {s['skill']}  (weeks {s['start_week']}-{s['end_week']})", expanded=s["priority"] == 1):
                    st.write(s["explanation"]); st.write("**Study:** " + "; ".join(s["topics"]))
                    st.write("**Prove it with:** " + s["practice_project"])
            if not r["plan"]["steps"]:
                st.success("No skill gaps to plan for.")
        with t3:
            for n, q in enumerate(r["questions"], 1):
                st.markdown(f"**{n}. {q['question']}**"); st.caption("Why: " + q["why"])
        with t4:
            cand = r["candidate"]
            st.write("**Skills found:** " + ", ".join(s for s, v in cand["skills"].items() if v["strength"] != "implied"))
            if cand["unrecognised_skills"]:
                st.write("**Not scored (unknown to the knowledge base):** " + ", ".join(cand["unrecognised_skills"]))
            st.write("**Education:** " + ("; ".join(e["text"] for e in cand["education"]) or "not found"))
        st.download_button("Download report (Markdown)", to_markdown(r), "job_prep_report.md")