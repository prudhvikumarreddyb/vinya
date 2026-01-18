# core/resume_exporter.py
"""
Resume Exporter
Exports resume text to PDF and DOCX.

PDF  -> reportlab
DOCX -> python-docx
"""

from pathlib import Path
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

from docx import Document


# ==================================================
# PATHS
# ==================================================
EXPORT_DIR = Path("data/exports")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ==================================================
# PDF EXPORT
# ==================================================
def export_resume_pdf(text: str) -> Path:
    """
    Export resume text to PDF.
    Returns generated file path.
    """
    filename = f"resume_{_timestamp()}.pdf"
    path = EXPORT_DIR / filename

    styles = getSampleStyleSheet()
    story = []

    for block in text.split("\n"):
        if block.strip():
            story.append(Paragraph(block, styles["Normal"]))
        story.append(Spacer(1, 6))

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    doc.build(story)
    return path


# ==================================================
# DOCX EXPORT
# ==================================================
def export_resume_docx(text: str) -> Path:
    """
    Export resume text to DOCX.
    Returns generated file path.
    """
    filename = f"resume_{_timestamp()}.docx"
    path = EXPORT_DIR / filename

    doc = Document()

    for line in text.split("\n"):
        doc.add_paragraph(line)

    doc.save(path)
    return path
