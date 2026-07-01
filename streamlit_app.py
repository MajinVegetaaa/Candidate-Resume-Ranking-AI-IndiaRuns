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

st.set_page_config(page_title="Redrob AI Ranker", layout="wide", page_icon="⚡")

# ── PREMIUM UI CUSTOMIZATION (CSS INJECTION) ─────────────────────────
st.markdown("""
<style>
    /* Import modern typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }
    
    /* App Background */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(20, 20, 30) 0%, rgb(10, 10, 15) 100%);
    }
    
    /* Beautiful Gradient Headers */
    h1, h2, h3 {
        background: -webkit-linear-gradient(45deg, #FF6B6B, #845EC2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    
    /* Primary Button Styling */
    .stButton > button {
        background: linear-gradient(90deg, #FF6B6B 0%, #845EC2 100%);
        color: white !important;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(132, 94, 194, 0.4);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(132, 94, 194, 0.7);
    }
    
    /* Text Areas & File Uploaders (Glassmorphism) */
    .stTextArea > div > div > textarea {
        background-color: rgba(255, 255, 255, 0.03) !important;
        color: #E2E2E2 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px;
        font-family: monospace;
    }
    
    [data-testid="stFileUploadDropzone"] {
        background-color: rgba(255, 255, 255, 0.02);
        border: 1px dashed rgba(255, 255, 255, 0.2);
        border-radius: 15px;
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        background-color: rgba(255, 255, 255, 0.05);
        border-color: rgba(132, 94, 194, 0.8);
    }
    
    /* Alert / Callout Boxes */
    .stAlert {
        border-radius: 12px !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 3.5rem !important;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #00C9FF, #92FE9D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Dataframes */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Custom divider */
    hr {
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
</style>
""", unsafe_allow_html=True)


st.title("⚡ Redrob Intelligent AI Ranker")
st.markdown("""
<div style="color: #A0A0B0; font-size: 1.1rem; margin-bottom: 2rem;">
Official Evaluation Sandbox for the IndiaRuns AI Hackathon. Fully spec-compliant End-to-End execution.
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🚀 End-to-End Execution", "🔬 Live Inspector"])

with tab1:
    st.markdown("### Batch Evaluation (Phases 1-4)")
    st.markdown("<p style='color: #888;'>Upload a `candidates.jsonl` file to automatically run the heuristic rules engine and PyTorch semantic models (Bi-Encoder ➔ Cross-Encoder).</p>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Drop candidates.jsonl here (≤ 500 candidates)", type=["jsonl", "json"])
    
    if uploaded_file is not None:
        if st.button("Execute Deep Ranking Pipeline", type="primary", width='stretch'):
            with st.spinner("Initializing neural networks... Please do not refresh."):
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
                        st.error("🚨 Pipeline crashed during execution.")
                        with st.expander("View Error Traceback", expanded=True):
                            st.code(result.stderr)
                    else:
                        st.success(f"✨ Pipeline completed successfully in {time.time() - start_time:.1f}s!")
                        
                        with st.expander("Terminal Logs"):
                            st.code(result.stdout)
                            
                        if os.path.exists(tmp_out_path):
                            st.markdown("<hr>", unsafe_allow_html=True)
                            st.markdown("### Top Ranked Candidates")
                            df = pd.read_csv(tmp_out_path)
                            st.dataframe(df, width='stretch')
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            csv_data = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Export Final submission.csv",
                                data=csv_data,
                                file_name="submission.csv",
                                mime="text/csv",
                                type="primary",
                                width='stretch'
                            )
                except Exception as e:
                    st.error(f"Error executing pipeline: {e}")
                finally:
                    if os.path.exists(tmp_in_path): os.remove(tmp_in_path)
                    if os.path.exists(tmp_out_path): os.remove(tmp_out_path)

with tab2:
    st.markdown("### Live Candidate Inspector")
    st.markdown("<p style='color: #888;'>Paste a single candidate JSON object to instantly preview their Phase 1 Sub-Scores, penalty triggers, and AI Reasoning logic.</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        candidate_json = st.text_area("Paste Raw JSON Object", height=500)
        
    with col2:
        st.markdown("<br>", unsafe_allow_html=True) # spacer
        if st.button("Simulate AI Judgment", type="primary", width='stretch'):
            if not candidate_json.strip():
                st.warning("Please paste a JSON object first.")
            else:
                try:
                    candidate = json.loads(candidate_json)
                    composite, is_hp, sub_scores = score_candidate(candidate, JD_CONFIG)
                    
                    if is_hp:
                        st.error("🚨 HONEYPOT ANOMALY DETECTED! SCORE NUKED TO 0.0")
                    
                    st.metric("Heuristic Score (Phase 1)", f"{composite:.4f}")
                    
                    st.markdown("### 📊 Sub-Score Matrix")
                    st.json(sub_scores)
                    
                    st.markdown("### 🧠 AI Reasoning")
                    reasoning = generate_reasoning(candidate, composite, 1)
                    st.info(reasoning)
                except json.JSONDecodeError:
                    st.error("Invalid JSON. Please ensure it is properly formatted.")
                except Exception as e:
                    st.error(f"Error evaluating JSON: {e}")
