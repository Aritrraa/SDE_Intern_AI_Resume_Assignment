import os
import json
import streamlit as st
import pandas as pd
from pathlib import Path

from src.pipeline import run_pipeline

# ---------------------------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Resume Screening System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Set custom minimal CSS
st.markdown("""
<style>
    .stProgress .st-bo { background-color: #4CAF50; }
    .card { padding: 15px; border-radius: 5px; border: 1px solid #ddd; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)


def load_previous_results(output_path: str) -> dict | None:
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def render_dashboard(results: dict):
    summary = results["batch_summary"]

    st.header("Batch Summary")
    cols = st.columns(5)
    cols[0].metric("Total Resumes", summary["total_resumes"])
    cols[1].metric("Parsed", summary["successfully_parsed"])
    cols[2].metric("Eligible", summary["eligible"])
    cols[3].metric("Rejected", summary["rejected"])
    cols[4].metric("Failed", summary["failed_unreadable"])

    st.divider()
    
    tab1, tab2 = st.tabs(["Top Candidates", "Rejected Candidates"])
    
    with tab1:
        st.subheader("Eligible Candidates")
        ranked = results["ranked_candidates"]
        if not ranked:
            st.info("No eligible candidates found.")
        else:
            # Build a dataframe for the overview table
            df_data = []
            for c in ranked:
                bd = c["score_breakdown"]
                df_data.append({
                    "Rank": c["rank"],
                    "Name": c["candidate_name"],
                    "Total Score": c["total_score"],
                    "AI (40)": bd["ai_project_depth"],
                    "Python (30)": bd["python_backend"],
                    "Cloud (15)": bd["cloud_fullstack"],
                    "GitHub (10)": bd["github"],
                    "Eng (5)": bd["engineering_depth"],
                    "File": c["source_file"],
                })
            
            df = pd.DataFrame(df_data).set_index("Rank")
            st.dataframe(df, use_container_width=True)
            
            st.subheader("Detailed Breakdown")
            for c in ranked:
                with st.expander(f"#{c['rank']} - {c['candidate_name']} ({c['total_score']} pts)"):
                    scol1, scol2 = st.columns([2, 1])
                    
                    with scol1:
                        st.markdown(f"**Email:** {c['email'] or 'N/A'}")
                        if c["github_url"]:
                            st.markdown(f"**GitHub:** [{c['github_url']}]({c['github_url']})")
                            st.markdown(f"*{c['github_summary']}*")
                        
                        st.markdown(f"**Project Summary:**\n{c['project_summary']}")
                        
                        st.markdown("**Evidence Found:**")
                        for e in c["evidence"]:
                            st.markdown(f"- {e}")
                            
                        # LLM additions
                        llm = c.get("llm_assessment")
                        if llm:
                            st.markdown("**🤖 LLM Semantic Analysis:**")
                            if llm.get("ai_implementation_evidence"):
                                st.markdown("*AI Implementations:* " + "; ".join(llm["ai_implementation_evidence"]))
                            if llm.get("python_backend_evidence"):
                                st.markdown("*Backend Implementations:* " + "; ".join(llm["python_backend_evidence"]))
                            if llm.get("ai_depth_rating"):
                                st.markdown(f"*AI Depth Rating:* **{llm['ai_depth_rating'].upper()}**")

                    with scol2:
                        st.markdown("**Strengths:**")
                        for s in c["strengths"]:
                            st.success(s)
                            
                        st.markdown("**Concerns:**")
                        for conc in c["concerns"]:
                            st.warning(conc)
                            
                        if c["penalties"]:
                            st.markdown("**Penalties Applied:**")
                            for p in c["penalties"]:
                                st.error(p)

    with tab2:
        st.subheader("Rejected Candidates")
        rejected = results["rejected_candidates"]
        if not rejected:
            st.info("No candidates were rejected.")
        else:
            for c in rejected:
                with st.container():
                    st.markdown(f"**{c['candidate_name']}** (`{c['source_file']}`)")
                    for r in c["rejection_reasons"]:
                        st.error(r)
                    st.divider()


def main():
    st.sidebar.title("AI Resume Screener")
    
    input_dir = st.sidebar.text_input("Input Directory", "./resumes")
    output_file = st.sidebar.text_input("Output JSON", "./output/results.json")
    
    enable_github = st.sidebar.checkbox("Enable GitHub Enrichment", value=True)
    enable_llm = st.sidebar.checkbox("Enable LLM Assessment", value=False, help="Requires API key in environment variables")
    
    st.sidebar.divider()
    
    if st.sidebar.button("Run Pipeline", type="primary"):
        if not os.path.exists(input_dir):
            st.sidebar.error("Input directory does not exist!")
            return
            
        with st.spinner("Running pipeline..."):
            try:
                Path(output_file).parent.mkdir(parents=True, exist_ok=True)
                results = run_pipeline(
                    input_dir=input_dir, 
                    enable_github=enable_github, 
                    enable_llm=enable_llm
                )
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                st.session_state["results"] = results
                st.success("Pipeline completed!")
            except Exception as e:
                st.error(f"Pipeline failed: {e}")
                
    st.sidebar.divider()
    st.sidebar.markdown("""
    **Hard Filters:**
    1. Must show Python evidence
    2. Must show AI/Agentic evidence
    
    **Weights (100 pts):**
    - AI Project Depth (40)
    - Python Backend (30)
    - Cloud/Fullstack (15)
    - GitHub (10)
    - Eng Depth (5)
    """)

    # Render results
    if "results" in st.session_state:
        render_dashboard(st.session_state["results"])
    else:
        prev = load_previous_results(output_file)
        if prev:
            st.info(f"Loaded previous results from `{output_file}`. Click 'Run Pipeline' to re-run.")
            render_dashboard(prev)
        else:
            st.info("No results loaded. Click 'Run Pipeline' to start.")


if __name__ == "__main__":
    main()
