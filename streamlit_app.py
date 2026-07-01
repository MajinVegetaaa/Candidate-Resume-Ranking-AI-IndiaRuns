import streamlit as st
import json
import os
import subprocess
import pandas as pd
import tempfile

st.set_page_config(page_title="Redrob Ranker - End-to-End Sandbox", layout="wide")

st.title("🤖 Redrob Ranker - Full Pipeline Sandbox")
st.markdown("""
According to the Hackathon Spec, this sandbox runs the **entire ranking system end-to-end** 
(Phase 1 Rules + Phase 2 Bi-Encoder + Phase 3 Cross-Encoder) on a small subset of candidates 
and generates the final Ranked CSV.
""")

uploaded_file = st.file_uploader("Upload a small candidates.jsonl file (≤ 500 candidates)", type=["jsonl", "json"])

if uploaded_file is not None:
    st.success(f"File uploaded: {uploaded_file.name}")
    
    if st.button("Run End-to-End Pipeline", type="primary"):
        with st.spinner("Running the full AI ranking pipeline... This may take a minute as it loads the semantic models."):
            # 1. Save uploaded file to a temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as tmp_in:
                tmp_in.write(uploaded_file.getvalue())
                tmp_in_path = tmp_in.name
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_out:
                tmp_out_path = tmp_out.name
                
            try:
                # 2. Run the actual rank.py pipeline as a subprocess
                result = subprocess.run(
                    ["python3", "rank.py", "--candidates", tmp_in_path, "--out", tmp_out_path],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    st.error("Pipeline crashed!")
                    st.code(result.stderr)
                else:
                    st.success("Pipeline completed successfully!")
                    
                    # Show logs
                    with st.expander("View Pipeline Logs"):
                        st.code(result.stdout)
                        
                    # 3. Read and display the CSV
                    if os.path.exists(tmp_out_path):
                        df = pd.read_csv(tmp_out_path)
                        st.markdown("### Top Ranked Candidates")
                        st.dataframe(df)
                        
                        # 4. Provide Download Button
                        csv_data = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Final submission.csv",
                            data=csv_data,
                            file_name="submission.csv",
                            mime="text/csv",
                        )
                        
            except Exception as e:
                st.error(f"Error executing pipeline: {e}")
            
            finally:
                # Cleanup temp files
                if os.path.exists(tmp_in_path): os.remove(tmp_in_path)
                if os.path.exists(tmp_out_path): os.remove(tmp_out_path)
