"""
Email sender via Gmail SMTP. Requires an App Password (not your regular Gmail password).

Setup:
  1. Enable 2FA: https://myaccount.google.com/security
  2. Generate App Password: https://myaccount.google.com/apppasswords
  3. Put the 16-char password in .env as SMTP_PASSWORD
"""
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()


def is_email_configured() -> bool:
    return all([
        os.getenv("SMTP_HOST"),
        os.getenv("SMTP_USER"),
        os.getenv("SMTP_PASSWORD"),
        os.getenv("SMTP_PASSWORD") != "your_16_char_app_password",
    ])


def _build_html_body(product_description: str, rationales: List[Dict]) -> str:
    rows = ""
    for i, r in enumerate(rationales[:5], 1):
        rows += f"""
        <tr>
          <td style="padding:10px; border-bottom:1px solid #eee; vertical-align:top;
                     font-weight:bold; color:#1f4e79; width:120px;">{r['standard']}</td>
          <td style="padding:10px; border-bottom:1px solid #eee; color:#333;">
            {r.get('rationale', '')}
          </td>
        </tr>"""

    return f"""<!doctype html>
<html><body style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;
                   background:#f7f9fc; padding: 20px; color:#2b2b2b;">
  <div style="background:white; padding: 30px; border-radius:8px;
              box-shadow: 0 1px 3px rgba(0,0,0,0.06);">
    <h1 style="color:#1f4e79; margin-top:0;">Your BIS Compliance Report</h1>
    <p style="color:#666; font-size:14px;">
      Below are the BIS standards we identified as most relevant to your product.
      A detailed PDF report is attached to this email.
    </p>

    <div style="background:#f7f9fc; padding:14px; border-left:4px solid #1f4e79;
                margin: 20px 0; border-radius:3px;">
      <strong>Product:</strong><br>{product_description}
    </div>

    <h3 style="color:#1f4e79;">Recommended Standards</h3>
    <table style="width:100%; border-collapse:collapse; font-size:14px;">
      {rows}
    </table>

    <p style="color:#666; font-size:12px; margin-top:30px;
              border-top:1px solid #eee; padding-top:15px;">
      This is an AI-generated guidance report. Verify all details with the
      Bureau of Indian Standards (bis.gov.in) before making business decisions.
    </p>
  </div>
</body></html>"""


def send_report_email(
    to_address: str,
    product_description: str,
    rationales: List[Dict],
    pdf_bytes: bytes,
    pdf_filename: str = "BIS_Compliance_Report.pdf",
) -> Dict:
    """
    Send the compliance report to the user. Returns {"success": bool, "message": str}.
    """
    if not is_email_configured():
        return {
            "success": False,
            "message": "Email not configured. Set SMTP_USER and SMTP_PASSWORD in .env",
        }

    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_name = os.getenv("SMTP_FROM_NAME", "BIS Standards Recommender")

    msg = EmailMessage()
    msg["Subject"] = "Your BIS Standards Compliance Report"
    msg["From"] = formataddr((from_name, user))
    msg["To"] = to_address

    msg.set_content(
        f"""Hello,

Please find attached your BIS Standards Compliance Report.

Product: {product_description}

Top recommended standards:
""" + "\n".join(f"  • {r['standard']}" for r in rationales[:5]) + """

A detailed PDF report is attached.

— BIS Standards Recommender
"""
    )

    msg.add_alternative(
        _build_html_body(product_description, rationales),
        subtype="html",
    )
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=pdf_filename,
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=context)
            server.login(user, password)
            server.send_message(msg)
        return {"success": True, "message": f"Report sent to {to_address}"}
    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "Authentication failed. Check your Gmail App Password.",
        }
    except Exception as e:
        return {"success": False, "message": f"Email failed: {e}"}