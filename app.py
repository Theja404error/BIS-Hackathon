"""
Streamlit UI for BIS Standards Recommender.

Architecture for language switching:
  - Always store ENGLISH originals in session_state.original_rationales
  - On every render, translate fresh from originals to the selected language
  - This means switching languages NEVER compounds errors
  - Translation is cached per (query, language) pair to avoid re-calling LLM
"""
import streamlit as st
from datetime import datetime

from src.rag_pipeline import RAGPipeline
from src.report import build_report
from src.emailer import send_report_email, is_email_configured
from src.translator import translate_rationales, SUPPORTED

st.set_page_config(
    page_title="BIS Standards Recommender",
    page_icon="🏗️",
    layout="wide",
)

# ---------- Styles ----------
st.markdown(
    """
    <style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1f4e79; margin-bottom: 0; }
    .sub-header { color: #555; font-size: 1.05rem; margin-bottom: 1.5rem; }
    .std-card {
        background: #f7f9fc; border-left: 4px solid #1f4e79;
        padding: 1rem 1.2rem; margin: 0.6rem 0; border-radius: 4px;
    }
    .std-code { font-weight: 700; color: #1f4e79; font-size: 1.1rem; }
    .history-item {
        padding: 8px 12px; background: #f0f4f8; border-radius: 4px;
        margin: 4px 0; font-size: 0.9rem;
    }
    .email-success {
        background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
        color: white; padding: 16px 20px; border-radius: 6px;
        font-size: 1.05rem; font-weight: 600; margin: 12px 0;
        box-shadow: 0 2px 6px rgba(40,167,69,0.25);
    }
    .email-error {
        background: #dc3545; color: white; padding: 16px 20px;
        border-radius: 6px; font-size: 1rem; margin: 12px 0;
    }
    .lang-banner {
        background: #fff3cd; color: #664d03; padding: 8px 14px;
        border-radius: 4px; font-size: 0.9rem; margin: 6px 0;
        border-left: 3px solid #ffc107;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="main-header">🏗️ BIS Standards Recommendation Engine</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">For Indian MSEs — describe your product, get applicable BIS standards, '
    'and download a complete compliance report.</p>',
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Loading RAG pipeline (first time only)...")
def load_pipeline():
    return RAGPipeline()


pipe = load_pipeline()


# ---------- Cached translation helper ----------
@st.cache_data(show_spinner=False)
def get_translated_rationales(rationales_key: str, _rationales: list, language: str):
    """
    Cache translations per (query_hash, language).
    rationales_key is just used as a cache key; _rationales is the actual data
    (underscore prefix tells Streamlit not to hash it).
    """
    if language == "English":
        return _rationales
    return translate_rationales(_rationales, language)


# ---------- Session state ----------
if "history" not in st.session_state:
    st.session_state.history = []
if "current_query" not in st.session_state:
    st.session_state.current_query = ""
if "current_retrieval" not in st.session_state:
    # Stores the original (English) result from RAGPipeline.query()
    st.session_state.current_retrieval = None
if "email_status" not in st.session_state:
    st.session_state.email_status = None


# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ Options")

    language = st.selectbox(
        "Display language",
        options=list(SUPPORTED.keys()),
        index=0,
        help="Translates rationale text. IS codes always shown in English.",
        key="language_selector",
    )

    if language != "English":
        st.markdown(
            f'<div class="lang-banner">🌐 Showing rationale in <b>{language}</b>. '
            f'IS codes remain in English for unambiguous reference.</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("💡 Try an example")
    examples = [
        "53 grade ordinary portland cement for high-rise buildings",
        "TMT steel bars Fe500 grade for RCC construction",
        "Coarse aggregates for concrete, 20mm nominal size",
        "Ready-mix concrete M25 grade for slab casting",
        "Fly ash for use in cement and concrete",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex}", use_container_width=True):
            st.session_state["query_input"] = ex

    st.divider()
    st.subheader("📜 Query History")
    if not st.session_state.history:
        st.caption("No queries yet this session.")
    else:
        for item in reversed(st.session_state.history[-10:]):
            short = item["query"][:50] + "…" if len(item["query"]) > 50 else item["query"]
            st.markdown(
                f'<div class="history-item"><b>{item["timestamp"]}</b><br>{short}</div>',
                unsafe_allow_html=True,
            )

    st.divider()
    st.caption("Built on BIS SP 21 (Building Materials)")


# ---------- Tabs ----------
tab_single, tab_compare = st.tabs(["🔍 Find Standards", "⚖️ Compare 2 Products"])


# ============================================================
# TAB 1: SINGLE QUERY
# ============================================================
with tab_single:
    query = st.text_area(
        "Describe your product",
        value=st.session_state.get("query_input", ""),
        height=100,
        placeholder="e.g., We manufacture 53-grade cement for residential construction projects...",
        key="query_textarea",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        submit = st.button("🔍 Find Standards", type="primary", use_container_width=True)

    if submit and query.strip():
        with st.spinner("Retrieving relevant BIS standards..."):
            result = pipe.query(query, top_k=5)

        # Store the ENGLISH original. Never overwrite this with translated text.
        st.session_state.current_retrieval = result
        st.session_state.current_query = query
        st.session_state.email_status = None

        st.session_state.history.append({
            "query": query,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })
        st.rerun()
    elif submit:
        st.warning("Please enter a product description.")

    # ---------- Email status banner ----------
    if st.session_state.email_status:
        kind, msg = st.session_state.email_status
        if kind == "success":
            st.markdown(
                f'<div class="email-success">✅ {msg}</div>',
                unsafe_allow_html=True,
            )
            st.balloons()
        else:
            st.markdown(
                f'<div class="email-error">❌ {msg}</div>',
                unsafe_allow_html=True,
            )
        if st.button("Dismiss", key="dismiss_email"):
            st.session_state.email_status = None
            st.rerun()

    # ---------- Display result ----------
    if st.session_state.current_retrieval:
        retrieval = st.session_state.current_retrieval
        query_disp = st.session_state.current_query
        original_rationales = retrieval["rationales"]  # always English

        # Translate fresh on every render. Cached per (query, language).
        cache_key = f"{query_disp}|{language}"
        if language != "English":
            with st.spinner(f"Translating to {language}..."):
                display_rationales = get_translated_rationales(
                    cache_key, original_rationales, language
                )
        else:
            display_rationales = original_rationales

        m1, m2, m3 = st.columns(3)
        m1.metric("Standards found", len(retrieval["retrieved_standards"]))
        m2.metric("Latency", f"{retrieval['latency_seconds']}s")
        m3.metric("Source", "SP 21 (verified)")

        st.divider()
        st.subheader("📋 Recommended Standards")

        for i, rec in enumerate(display_rationales, 1):
            st.markdown(
                f"""
                <div class="std-card">
                    <div class="std-code">#{i} — {rec['standard']}</div>
                    <div style="margin-top: 0.4rem; color: #333;">{rec['rationale']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ---------- Report actions ----------
        st.divider()
        st.subheader("📄 Compliance Report")

        # PDF cache per (query, language)
        report_key = f"report_pdf_{hash(query_disp)}_{language}"
        if report_key not in st.session_state:
            with st.spinner("Generating PDF report..."):
                pdf_bytes = build_report(query_disp, display_rationales)
                st.session_state[report_key] = pdf_bytes
        pdf_bytes = st.session_state[report_key]

        col_a, col_b = st.columns([1, 2])

        with col_a:
            st.download_button(
                "⬇️ Download PDF Report",
                data=pdf_bytes,
                file_name=f"BIS_Compliance_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        with col_b:
            if not is_email_configured():
                st.info(
                    "📧 Email is not configured. Set `SMTP_USER` and `SMTP_PASSWORD` "
                    "(Gmail App Password) in your `.env` file."
                )
            else:
                email_addr = st.text_input(
                    "📧 Send report to email",
                    placeholder="user@example.com",
                    key="email_input",
                )
                if st.button("📨 Send Report", type="primary", use_container_width=True):
                    if not email_addr or "@" not in email_addr:
                        st.session_state.email_status = (
                            "error", "Please enter a valid email address."
                        )
                    else:
                        with st.spinner(f"Sending report to {email_addr}..."):
                            resp = send_report_email(
                                email_addr, query_disp,
                                display_rationales, pdf_bytes,
                            )
                        if resp["success"]:
                            st.session_state.email_status = (
                                "success",
                                f"Mail sent successfully to {email_addr}! Check your inbox.",
                            )
                        else:
                            st.session_state.email_status = ("error", resp["message"])
                    st.rerun()

        with st.expander("🔧 View raw output (for evaluation)"):
            st.json({
                "id": "current",
                "retrieved_standards": retrieval["retrieved_standards"],
                "latency_seconds": retrieval["latency_seconds"],
            })


# ============================================================
# TAB 2: COMPARE 2 PRODUCTS
# ============================================================
with tab_compare:
    st.markdown(
        "Compare the recommended standards for two different products side by side. "
        "Useful for MSEs evaluating product variants or competing materials."
    )

    cc1, cc2 = st.columns(2)
    with cc1:
        product_a = st.text_area("Product A", placeholder="e.g., 53 grade OPC cement",
                                 key="prod_a", height=80)
    with cc2:
        product_b = st.text_area("Product B", placeholder="e.g., Portland Pozzolana Cement (PPC)",
                                 key="prod_b", height=80)

    if st.button("⚖️ Compare", type="primary"):
        if not product_a.strip() or not product_b.strip():
            st.warning("Please enter both products.")
        else:
            with st.spinner("Analyzing both products..."):
                res_a = pipe.query(product_a, top_k=5)
                res_b = pipe.query(product_b, top_k=5)

            # Translate (cached) per side
            if language != "English":
                with st.spinner(f"Translating to {language}..."):
                    rats_a = get_translated_rationales(
                        f"{product_a}|{language}|A", res_a["rationales"], language
                    )
                    rats_b = get_translated_rationales(
                        f"{product_b}|{language}|B", res_b["rationales"], language
                    )
            else:
                rats_a = res_a["rationales"]
                rats_b = res_b["rationales"]

            st.divider()
            cols = st.columns(2)
            for col, prod, res, rats in [
                (cols[0], product_a, res_a, rats_a),
                (cols[1], product_b, res_b, rats_b),
            ]:
                with col:
                    st.markdown(f"#### 🏷️ {prod[:60]}")
                    st.caption(f"Latency: {res['latency_seconds']}s")
                    for i, rec in enumerate(rats, 1):
                        st.markdown(
                            f"""
                            <div class="std-card">
                              <div class="std-code">#{i} — {rec['standard']}</div>
                              <div style="margin-top:0.3rem; color:#444; font-size:0.92rem;">
                                {rec['rationale']}
                              </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            set_a = set(res_a["retrieved_standards"])
            set_b = set(res_b["retrieved_standards"])
            overlap = set_a & set_b
            if overlap:
                st.divider()
                st.success(f"📌 **{len(overlap)} standard(s) apply to BOTH products:** "
                           + ", ".join(sorted(overlap)))
            else:
                st.info("No overlapping standards — these products are governed by different regulations.")