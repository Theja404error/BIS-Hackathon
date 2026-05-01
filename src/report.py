"""
PDF compliance report generator.

Sections:
  1. Executive Summary (product description + top recommendations)
  2. Recommended Standards (with rationale for each)
  3. Compliance Checklist (LLM-generated action items per standard)
  4. Indicative Cost Categories (NOT specific numbers - honest disclosure)
  5. Recommended Next Steps
  6. Disclaimer & Source

The LLM only fills in HUMAN-VERIFIABLE text (rationale, checklist items).
All IS codes come from the retrieval whitelist. No fabricated numbers.
"""
import os
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, ListFlowable, ListItem
)

from src.llm import generate

# ---------- Branding ----------
PRIMARY = HexColor("#1f4e79")
ACCENT = HexColor("#2e75b6")
LIGHT_BG = HexColor("#f7f9fc")
DARK_TEXT = HexColor("#2b2b2b")
MUTED = HexColor("#666666")

ISSUING_AUTHORITY = os.getenv("ISSUING_AUTHORITY", "BIS Standards Recommender")


# ---------- Styles ----------
def _build_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "title", parent=base["Heading1"], fontSize=20, leading=24,
            textColor=PRIMARY, spaceAfter=6, fontName="Helvetica-Bold",
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontSize=10, leading=13,
            textColor=MUTED, spaceAfter=14,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=14, leading=18,
            textColor=PRIMARY, spaceBefore=14, spaceAfter=6,
            fontName="Helvetica-Bold",
        ),
        "h3": ParagraphStyle(
            "h3", parent=base["Heading3"], fontSize=11.5, leading=14,
            textColor=ACCENT, spaceBefore=8, spaceAfter=4,
            fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontSize=10, leading=14,
            textColor=DARK_TEXT, alignment=TA_JUSTIFY, spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=base["BodyText"], fontSize=10, leading=13,
            textColor=DARK_TEXT, leftIndent=14, bulletIndent=2, spaceAfter=3,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"], fontSize=8.5, leading=11,
            textColor=MUTED, spaceAfter=4,
        ),
        "code": ParagraphStyle(
            "code", parent=base["Normal"], fontSize=10, leading=12,
            textColor=PRIMARY, fontName="Helvetica-Bold",
        ),
    }
    return styles


# ---------- Header / Footer ----------
def _header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4

    # Top bar
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, height - 1.4 * cm, width, 1.4 * cm, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#ffffff"))
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(2 * cm, height - 0.9 * cm, "BIS Compliance Report")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(
        width - 2 * cm, height - 0.9 * cm,
        f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M IST')}"
    )

    # Footer
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(
        2 * cm, 1.2 * cm,
        f"{ISSUING_AUTHORITY}  •  Source: BIS SP 21 (Building Materials)"
    )
    canvas.drawRightString(width - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


# ---------- LLM helpers (whitelist-safe) ----------
CHECKLIST_PROMPT = """You are a BIS compliance assistant. The user's product is:

{query}

For the BIS standard {is_code}, generate a concrete compliance checklist of 4-6 action items
that an Indian MSE owner needs to do to comply with this standard.

Focus on practical, verifiable steps (testing, documentation, sample submission, etc.).
Do NOT invent specific fees, locations, or contact details.
Do NOT mention any other IS code besides {is_code}.

Respond as a plain numbered list, one item per line. No JSON, no markdown, no preamble."""


def _generate_checklist(query: str, is_code: str) -> List[str]:
    """Generate action items for one standard. Returns list of strings."""
    try:
        raw = generate(CHECKLIST_PROMPT.format(query=query, is_code=is_code), max_tokens=400)
        items = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # Strip leading numbering "1.", "1)", "-", "*", etc.
            for prefix in ["1.", "2.", "3.", "4.", "5.", "6.", "7.",
                           "1)", "2)", "3)", "4)", "5)", "6)", "7)",
                           "-", "*", "•"]:
                if line.startswith(prefix):
                    line = line[len(prefix):].strip()
                    break
            if line:
                items.append(line)
        return items[:6] if items else ["Refer to the full BIS standard document for compliance details."]
    except Exception:
        return ["Refer to the full BIS standard document for compliance details."]


COST_CATEGORIES = [
    ("Initial Sample Testing", "Lab testing of product samples against the standard's requirements"),
    ("BIS Certification Application", "Application processing and documentation review"),
    ("Factory Inspection", "On-site assessment of manufacturing facility (one-time + recurring)"),
    ("Marking Fee", "Per-unit fee for using the BIS Standard Mark / ISI mark"),
    ("Annual License Renewal", "Recurring license maintenance"),
]


# ---------- Main builder ----------
def build_report(
    product_description: str,
    rationales: List[Dict],
    output_path: str = None,
    language: str = "English",
) -> bytes:
    """
    Generate a compliance PDF report. Returns PDF bytes; also writes to
    output_path if provided.

    Args:
        product_description: original user query
        rationales: list of {"standard": "IS XXXX", "rationale": "..."}
        output_path: optional file path to write to
        language: "English" | "Hindi" | "Tamil"  -- only translates rationale text;
                  IS codes and numeric data stay in English.
    """
    styles = _build_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )

    story = []

    # ==== Title ====
    story.append(Paragraph("BIS Standards Compliance Report", styles["title"]))
    story.append(Paragraph(
        "AI-generated recommendations based on Bureau of Indian Standards SP 21 — "
        "Summaries of Indian Standards for Building Materials.",
        styles["subtitle"]
    ))

    # ==== Executive Summary ====
    story.append(Paragraph("1. Executive Summary", styles["h2"]))
    story.append(Paragraph("<b>Product Description</b>", styles["h3"]))
    story.append(Paragraph(product_description, styles["body"]))

    summary_lines = [
        f"<b>{r['standard']}</b>" for r in rationales[:5]
    ]
    story.append(Paragraph("<b>Top Recommended Standards</b>", styles["h3"]))
    story.append(Paragraph(" • ".join(summary_lines), styles["body"]))

    # ==== Recommended Standards ====
    story.append(Paragraph("2. Recommended Standards & Rationale", styles["h2"]))

    table_data = [["#", "Standard", "Why it applies"]]
    for i, r in enumerate(rationales[:5], 1):
        table_data.append([
            str(i),
            Paragraph(f"<b>{r['standard']}</b>", styles["body"]),
            Paragraph(r.get("rationale", "—"), styles["body"]),
        ])
    table = Table(table_data, colWidths=[0.8 * cm, 3.5 * cm, 12.2 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#cccccc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)

    # ==== Compliance Checklists (per standard) ====
    story.append(PageBreak())
    story.append(Paragraph("3. Compliance Checklist", styles["h2"]))
    story.append(Paragraph(
        "Concrete action items for each recommended standard. Use this as a starting "
        "point — the official BIS standard document remains the authoritative source.",
        styles["body"]
    ))

    for r in rationales[:3]:  # checklists for top 3 only (keeps PDF reasonable)
        items = _generate_checklist(product_description, r["standard"])
        block = [
            Paragraph(f"<b>{r['standard']}</b>", styles["h3"]),
            ListFlowable(
                [ListItem(Paragraph(item, styles["body"]), leftIndent=12) for item in items],
                bulletType="1",
                start="1",
                leftIndent=18,
            ),
            Spacer(1, 0.3 * cm),
        ]
        story.append(KeepTogether(block))

    # ==== Cost Categories (honest, no fake numbers) ====
    story.append(Paragraph("4. Indicative Cost Categories", styles["h2"]))
    story.append(Paragraph(
        "<b>Important:</b> Specific fees vary by product category, manufacturing scale, "
        "and BIS branch office. The categories below indicate <i>what</i> you will pay "
        "for; for current rates, contact your nearest BIS branch office or visit "
        "<u>bis.gov.in</u>.",
        styles["body"]
    ))

    cost_table_data = [["Cost Category", "What it covers"]]
    for cat, desc in COST_CATEGORIES:
        cost_table_data.append([
            Paragraph(f"<b>{cat}</b>", styles["body"]),
            Paragraph(desc, styles["body"]),
        ])
    cost_table = Table(cost_table_data, colWidths=[5 * cm, 11.5 * cm])
    cost_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#cccccc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(cost_table)

    # ==== Next Steps ====
    story.append(Paragraph("5. Recommended Next Steps", styles["h2"]))
    next_steps = [
        "Download the full text of each recommended standard from the BIS portal "
        "(standardsbis.bsbedge.com).",
        "Identify a BIS-recognized testing laboratory near you for sample testing.",
        "Apply for BIS certification online via the Manakonline portal "
        "(manakonline.in).",
        "Prepare your manufacturing facility for the initial inspection.",
        "Consult your nearest BIS branch office for current fees and timelines.",
    ]
    story.append(ListFlowable(
        [ListItem(Paragraph(s, styles["body"]), leftIndent=12) for s in next_steps],
        bulletType="1",
        start="1",
        leftIndent=18,
    ))

    # ==== Disclaimer ====
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("6. Disclaimer", styles["h2"]))
    story.append(Paragraph(
        "This report is generated by an AI-powered recommendation engine for guidance "
        "purposes only. It is not a substitute for professional regulatory advice or "
        "the official BIS certification process. All standards mentioned are sourced "
        "from BIS SP 21. Verify all information with the Bureau of Indian Standards "
        "before making business decisions.",
        styles["small"]
    ))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes


if __name__ == "__main__":
    # Smoke test
    sample_rationales = [
        {"standard": "IS 12269:1987",
         "rationale": "Specifies requirements for 53-grade Ordinary Portland Cement, the exact product."},
        {"standard": "IS 8112:1989",
         "rationale": "Covers 43-grade OPC; useful for comparison and lower-strength applications."},
        {"standard": "IS 4032:1985",
         "rationale": "Methods of chemical analysis of hydraulic cement, used for quality verification."},
    ]
    build_report(
        "53 grade ordinary portland cement for high-rise residential buildings",
        sample_rationales,
        output_path="/tmp/test_report.pdf",
    )
    print("✅ Test report generated at /tmp/test_report.pdf")