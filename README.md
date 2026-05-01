# 🏗️ BIS Standards Recommendation Engine

> An AI-powered RAG system that helps Indian MSEs identify applicable Bureau of Indian Standards (BIS) for their products in seconds — instead of weeks.

**Built for:** BIS x SS Hackathon 2026 — AI / Retrieval-Augmented Generation Track
**Team:** Matsya N

---

## 🎯 The Problem We Solve

Indian Micro and Small Enterprises (MSEs) spend **2-6 weeks** identifying which BIS standards apply to their products. Compliance consultants charge **₹15,000-₹50,000 per product**, putting professional guidance out of reach for most micro-enterprises.

Our system reduces this to **under 2 seconds** — and it's free.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔍 **Hybrid RAG Pipeline** | BM25 + dense embeddings (BAAI/bge-small) fused via Reciprocal Rank Fusion |
| 🧠 **LLM Re-ranking** | Llama 3.3 70B (via Groq) ranks top candidates with rationale |
| 🛡️ **Zero Hallucinations** | Whitelist-constrained generation — LLM can only output retrieved IS codes |
| 📄 **PDF Compliance Reports** | 6-section branded report: rationale, checklist, cost categories, next steps |
| 📧 **Email Delivery** | Send reports straight to MSE inbox via Gmail SMTP |
| 🌐 **Multi-language** | Hindi & Tamil rationale display (IS codes always in English for unambiguity) |
| ⚖️ **Side-by-side Comparison** | Compare 2 products; auto-detects overlapping standards |
| 📜 **Query History** | Per-session sidebar of recent queries |

---

## 🏛️ System Architecture

```
                    ┌─────────────────────────────┐
                    │     User Product Query      │
                    └──────────────┬──────────────┘
                                   ▼
                ┌──────────────────────────────────┐
                │       HYBRID RETRIEVAL           │
                │  ┌────────────┐  ┌────────────┐  │
                │  │   BM25     │  │ BGE Dense  │  │
                │  │ (lexical)  │  │ (semantic) │  │
                │  └─────┬──────┘  └─────┬──────┘  │
                │        └──── RRF ─────┘          │
                └──────────────┬───────────────────┘
                               ▼ (top 10 candidates)
                    ┌──────────────────────┐
                    │   LLM Re-rank        │
                    │  Llama 3.3 70B       │
                    │  (temp = 0.1)        │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │ Whitelist Validator  │
                    │ (no hallucinations)  │
                    └──────────┬───────────┘
                               ▼
                    Top 3-5 Standards + Rationale
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
         📄 PDF Report   📧 Email Send   🌐 UI Display

Knowledge Base: BIS SP 21 (Building Materials) → 817 anchored chunks
```

---

## 📊 Performance

Evaluated on the public test set:

| Metric | Result | Target |
|--------|--------|--------|
| Hit Rate @3 | **100%** | > 80% |
| Avg Latency | **~1.4s** | < 5s |
| Hallucination Rate | **0%** | Whitelist-enforced |

> *Note: Numbers from sample queries during development. Real numbers on the hidden test set will be reported in `presentation.pdf` after running `eval_script.py`.*

---

## 🚀 Quick Start (5 minutes)

### Prerequisites

- Python 3.10+
- A free [Groq API key](https://console.groq.com/keys)
- (Optional) Gmail account with [App Password](https://myaccount.google.com/apppasswords) for email feature

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/Theja404404error/BIS-Hackathon.git
cd BIS-Hackathon

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # Mac/Linux
# Then open .env and add your GROQ_API_KEY

# 5. Drop SP 21 PDFs into data/raw_pdfs/

# 6. Build the search index (one-time, ~3 min)
python -m src.ingest
python -m src.retriever
```

### One-click scripts (Windows)

For convenience, the project ships with `.bat` files:

```bash
setup.bat        # Install dependencies (run once)
build_index.bat  # Build search index after dropping PDFs
run.bat          # Launch Streamlit app at localhost:8501
eval.bat         # Run inference.py on a test set
fix_deps.bat     # Fix groq/httpx version conflicts if they arise
```

### Run the app

```bash
streamlit run app.py
# Or simply: run.bat
```

Open http://localhost:8501 — the demo UI loads in ~10 seconds.

---

## 🧪 For Judges — Running Inference

The mandatory evaluation entry point is at the repo root:

```bash
python inference.py --input data/public_test_set.json --output data/results.json
```

**Input JSON format:**
```json
[
  {"id": "q1", "query": "53 grade ordinary portland cement"},
  {"id": "q2", "query": "TMT steel bars Fe500 grade"}
]
```

**Output JSON format (strict — matches eval schema):**
```json
[
  {
    "id": "q1",
    "retrieved_standards": ["IS 12269:1987", "IS 8112:1989", "IS 4032:1985"],
    "latency_seconds": 1.69
  }
]
```

To run the full evaluation:
```bash
python eval_script.py    # provided by organizers, drop in repo root
```

---

## 🎨 Design Decisions (Why this works)

### 1. Standard-aware chunking (vs naïve fixed-window)

Most RAG systems use 512-token sliding windows. **We don't.** BIS standards are atomic regulatory units — splitting `IS 12269:1987` across three chunks means retrieval can find half a standard's text but lose the title and code.

Our `src/ingest.py` detects IS code boundaries via regex and anchors each chunk to one standard's complete summary. The result: **817 atomic chunks, one per IS code**, indexed in FAISS + BM25.

### 2. Hybrid retrieval with Reciprocal Rank Fusion

- **BM25** (lexical) catches exact code lookups: user types "IS 8112" → match.
- **BGE-small** (semantic) catches paraphrases: "high-strength cement" → IS 12269.
- **RRF (k=60)** combines both ranks robustly without score normalization.

Empirically this adds 5-10 points on Hit@3 vs dense-only.

### 3. Whitelist-constrained LLM (the anti-hallucination trick)

The LLM never sees the full standards corpus. It only sees the **top 10 candidates returned by retrieval**, and its prompt says: *"Pick from this list. Do NOT invent codes."* Every output is then validated against the retrieved whitelist before display.

This makes hallucinated IS codes **structurally impossible**, not just unlikely.

### 4. Honest cost reporting (not LLM-fabricated numbers)

Our PDF report includes a "Cost Categories" section but **deliberately does not invent specific fees** (testing fees, BIS license costs). Those vary by product/region and the LLM would hallucinate them. Instead we show what categories of cost an MSE will face and direct them to bis.gov.in for current rates.

---

## 📂 Project Structure

```
BIS-Hackathon/
├── src/
│   ├── ingest.py          # PDF parsing → standard-aware chunking
│   ├── retriever.py       # Hybrid BM25 + dense + RRF
│   ├── rag_pipeline.py    # End-to-end: retrieve → re-rank → validate
│   ├── llm.py             # LLM provider wrapper (Groq / Gemini)
│   ├── report.py          # ReportLab PDF compliance report generator
│   ├── emailer.py         # Gmail SMTP email sender
│   └── translator.py      # Safe Hindi/Tamil translation (preserves IS codes)
│
├── data/
│   ├── raw_pdfs/          # Drop SP 21 PDFs here
│   ├── chunks.json        # Generated by ingest.py
│   ├── index/             # FAISS + BM25 indices (generated)
│   └── sample_test_set.json
│
├── inference.py           # MANDATORY judge entry point
├── eval_script.py         # Drop in from organizers
├── app.py                 # Streamlit UI
├── requirements.txt
├── .env.example           # Template (no secrets)
├── presentation.pdf       # 8-slide deck per rulebook spec
├── README.md
│
├── run.bat                # Launch app
├── setup.bat              # First-time install
├── build_index.bat        # Rebuild search index
├── eval.bat               # Run inference + eval
└── fix_deps.bat           # Fix dependency conflicts
```

---

## 🔧 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Embeddings** | `BAAI/bge-small-en-v1.5` via sentence-transformers |
| **Vector Store** | FAISS (IndexFlatIP for cosine similarity) |
| **Lexical Retrieval** | rank-bm25 |
| **LLM** | Llama 3.3 70B via Groq API (free tier, fast inference) |
| **PDF Parsing** | pdfplumber |
| **PDF Generation** | ReportLab |
| **UI** | Streamlit |
| **Email** | Python `smtplib` + Gmail SMTP |

---

## 🌍 Impact on MSEs

|  | Before | After |
|--|--------|-------|
| Time per product | 2-6 weeks | < 2 seconds |
| Cost per product | ₹15K-₹50K (consultant) | Free |
| Coverage | Whatever consultant happens to know | All standards in SP 21 |
| Languages | English only | English + Hindi + Tamil |
| Output | Verbal advice / Word doc | Branded PDF + email + checklist |

For India's **6.3 crore MSME ecosystem**, that's a 99%+ reduction in compliance discovery time at zero marginal cost.

---

## 🛠️ Configuration

Environment variables in `.env`:

```env
# LLM (required)
GROQ_API_KEY=your_groq_key_here
LLM_PROVIDER=groq                # or "gemini"

# Email (optional - for report sending)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_16_char_app_password   # NOT your regular Gmail password!
SMTP_FROM_NAME=BIS Standards Recommender

# Branding
ISSUING_AUTHORITY=BIS Standards Recommender
```

To use Gmail SMTP:
1. Enable 2FA on your Google account
2. Generate an App Password at https://myaccount.google.com/apppasswords
3. Paste the 16-character password into `SMTP_PASSWORD`

---

## 🧯 Troubleshooting

| Error | Fix |
|-------|-----|
| `Client.__init__() got an unexpected keyword argument 'proxies'` | Run `fix_deps.bat` or `pip install "groq>=0.13.0" "httpx>=0.27.2,<0.28"` |
| `No PDFs found in data/raw_pdfs` | Drop SP 21 PDFs into that folder, then run `build_index.bat` |
| `GROQ_API_KEY not set` | Copy `.env.example` to `.env` and add your key |
| `LLM re-ranking unavailable` (fallback message in UI) | Run `streamlit cache clear`, then refresh the app |
| Email "Authentication failed" | You're using your regular Gmail password — use an App Password instead |

---

## 👥 Team Matsya N

| Member | Role |
|--------|------|
| **Akshay D** | Pipeline & Backend |
| **Thejashwini M** | Frontend & Evaluation |
| **Tanusiri M** | Research & Documentation |

---

## 🙏 Acknowledgements

- **Bureau of Indian Standards** — for the SP 21 dataset
- **Groq** — for free, fast Llama 3.3 inference
- **Hugging Face / BAAI** — for the bge-small embedding model
- **Open-source community** — sentence-transformers, FAISS, rank-bm25, Streamlit, ReportLab

---

## 📜 License

This project is released under the MIT License — built for India's MSEs.

---

*Built with ❤️ for the BIS x SS Hackathon 2026.*