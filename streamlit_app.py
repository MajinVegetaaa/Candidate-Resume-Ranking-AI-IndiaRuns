import streamlit as st
import json
import os
import subprocess
import pandas as pd
import tempfile
import time

from rank import score_candidate
from pipeline.reasoning_generator import generate_reasoning
from config.jd_config import JD_CONFIG

st.set_page_config(page_title="Redrob Ranker Sandbox", layout="wide")

st.title("🏆 Redrob Intelligent Candidate Ranker")
st.markdown("""
Welcome to the Official Evaluation Sandbox for the IndiaRuns AI Hackathon.
This sandbox strictly adheres to the submission specification constraints.
""")

tab1, tab2 = st.tabs(["🚀 End-to-End Pipeline (Spec Compliant)", "🔬 Candidate Inspector (Phase 1)"])

with tab1:
    st.markdown("### 1. Batch Execution (Phases 1-4)")
    st.markdown("Upload a `candidates.jsonl` file to run the entire ranking architecture (Heuristics ➔ Bi-Encoder ➔ Cross-Encoder).")
    
    uploaded_file = st.file_uploader("Upload candidates.jsonl (≤ 500 candidates)", type=["jsonl", "json"])
    
    if uploaded_file is not None:
        if st.button("Execute Full Pipeline", type="primary"):
            with st.spinner("Initializing models and executing ranking... Please do not refresh."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as tmp_in:
                    tmp_in.write(uploaded_file.getvalue())
                    tmp_in_path = tmp_in.name
                    
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_out:
                    tmp_out_path = tmp_out.name
                    
                start_time = time.time()
                try:
                    result = subprocess.run(
                        ["python3", "rank.py", "--candidates", tmp_in_path, "--out", tmp_out_path],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        st.error("Pipeline crashed during execution.")
                        with st.expander("View Error Traceback", expanded=True):
                            st.code(result.stderr)
                    else:
                        st.success(f"Pipeline completed successfully in {time.time() - start_time:.1f}s!")
                        
                        with st.expander("View Execution Logs"):
                            st.code(result.stdout)
                            
                        if os.path.exists(tmp_out_path):
                            df = pd.read_csv(tmp_out_path)
                            st.markdown("### Top Ranked Candidates")
                            st.dataframe(df)
                            
                            csv_data = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Download Final submission.csv",
                                data=csv_data,
                                file_name="submission.csv",
                                mime="text/csv",
                                type="primary"
                            )
                except Exception as e:
                    st.error(f"Error executing pipeline: {e}")
                finally:
                    if os.path.exists(tmp_in_path): os.remove(tmp_in_path)
                    if os.path.exists(tmp_out_path): os.remove(tmp_out_path)

with tab2:
    st.markdown("### 2. Single Candidate Debugger")
    st.markdown("Paste a single candidate JSON to bypass the semantic models and instantly preview their Phase 1 Sub-Scores and AI Reasoning.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        candidate_json = st.text_area("Paste Candidate JSON", height=400)
        
    with col2:
        if st.button("Evaluate Candidate"):
            if not candidate_json.strip():
                st.warning("Please paste a JSON.")
            else:
                try:
                    candidate = json.loads(candidate_json)
                    composite, is_hp, sub_scores = score_candidate(candidate, JD_CONFIG)
                    
                    if is_hp:
                        st.error("🚨 HONEYPOT DETECTED! SCORE NUKED TO 0.0")
                    
                    st.metric("Phase 1 Base Score", f"{composite:.4f}")
                    st.json(sub_scores)
                    
                    st.markdown("### AI Reasoning Output")
                    reasoning = generate_reasoning(candidate, composite, 1)
                    st.info(reasoning)
                except Exception as e:
                    st.error(f"Error evaluating JSON: {e}")
