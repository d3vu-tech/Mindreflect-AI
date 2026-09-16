"""
PDF report generation for MindReflect AI.
Uses ReportLab to produce a well-structured wellness summary PDF.

DISCLAIMER included on every page: This report contains self-reported
wellness information and statistical observations. It is not a medical diagnosis.
"""

from datetime import date
from typing import Dict, List, Optional
import io

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False


DISCLAIMER_TEXT = (
    "This report contains self-reported wellness information and statistical observations. "
    "It is not a medical diagnosis, clinical assessment, or therapeutic advice. "
    "MindReflect AI is a wellness reflection tool and does not replace a qualified healthcare professional."
)


def is_pdf_available() -> bool:
    return _REPORTLAB_AVAILABLE


def generate_wellness_report(
    user_display_name: str,
    date_range: str,
    checkins: List[Dict],
    patterns: List[Dict],
    ai_summary: Optional[str],
    selected_journal_titles: Optional[List[str]],
    baseline: Dict,
    recent_averages: Dict,
    include_behavioral: bool = True,
) -> Optional[bytes]:
    """
    Generate a PDF wellness report and return it as bytes.
    Returns None if ReportLab is not installed.
    """
    if not _REPORTLAB_AVAILABLE:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="MindReflect Wellness Report",
    )

    styles = getSampleStyleSheet()
    accent = colors.HexColor("#3b82d4")
    muted = colors.HexColor("#57606a")
    bg_surface = colors.HexColor("#f7f8fa")

    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontSize=22, textColor=accent, spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    h1_style = ParagraphStyle(
        "H1", parent=styles["Heading1"],
        fontSize=14, textColor=accent, spaceBefore=14, spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=12, textColor=colors.HexColor("#1f2328"),
        spaceBefore=10, spaceAfter=3, fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, leading=14, textColor=colors.HexColor("#1f2328"),
        spaceAfter=4,
    )
    muted_style = ParagraphStyle(
        "Muted", parent=styles["Normal"],
        fontSize=9, leading=13, textColor=muted,
        spaceAfter=3,
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer", parent=styles["Normal"],
        fontSize=8, leading=11, textColor=muted,
        borderPad=6, backColor=bg_surface,
        borderWidth=1, borderColor=colors.HexColor("#e5e7eb"),
        spaceBefore=6, spaceAfter=6,
    )

    story = []

    # ── Header ──
    story.append(Paragraph("MindReflect AI", title_style))
    story.append(Paragraph("Wellness Reflection Report", h2_style))
    story.append(Paragraph(f"Prepared for: {user_display_name}", muted_style))
    story.append(Paragraph(f"Period: {date_range}", muted_style))
    story.append(Paragraph(f"Generated: {date.today().strftime('%d %B %Y')}", muted_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
    story.append(Spacer(1, 8))

    # ── Disclaimer ──
    story.append(Paragraph(f"⚠️  {DISCLAIMER_TEXT}", disclaimer_style))
    story.append(Spacer(1, 10))

    # ── Summary averages ──
    story.append(Paragraph("Wellness Summary", h1_style))

    metrics = [
        ("Mood (1–5)", recent_averages.get("mood"), baseline.get("mood")),
        ("Stress (1–5)", recent_averages.get("stress"), baseline.get("stress")),
        ("Sleep duration (hrs)", recent_averages.get("sleep_hours"), baseline.get("sleep_hours")),
        ("Sleep quality (1–5)", recent_averages.get("sleep_quality"), baseline.get("sleep_quality")),
        ("Energy (1–5)", recent_averages.get("energy"), baseline.get("energy")),
    ]

    table_data = [["Metric", "Report Period Avg", "30-day Baseline"]]
    for label, recent, base in metrics:
        r_str = f"{recent:.2f}" if recent is not None else "—"
        b_str = f"{base:.2f}" if base is not None else "—"
        table_data.append([label, r_str, b_str])

    tbl = Table(table_data, colWidths=[8 * cm, 4 * cm, 4 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_surface]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 10))

    # ── Check-in count ──
    if checkins:
        story.append(Paragraph(
            f"Check-ins included in this report: {len(checkins)}",
            muted_style
        ))
    story.append(Spacer(1, 6))

    # ── Detected patterns ──
    if patterns:
        story.append(Paragraph("Behavioral Pattern Observations", h1_style))
        story.append(Paragraph(
            "These are observational statistical patterns from self-reported data. "
            "They are not clinical findings or diagnoses.",
            muted_style
        ))
        story.append(Spacer(1, 6))

        for p in patterns:
            items = [
                [Paragraph(p.get("pattern_name", "Pattern"), h2_style)],
                [Paragraph(p.get("description", ""), body_style)],
                [Paragraph(f"Evidence: {p.get('evidence', '')}", muted_style)],
                [Paragraph(
                    f"Confidence: {p.get('confidence', '').capitalize()} | "
                    f"Data points: {p.get('data_points', 0)}",
                    muted_style
                )],
            ]
            for item in items:
                story.append(item[0])
            story.append(Spacer(1, 6))

    # ── AI Wellness Summary ──
    if ai_summary:
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
        story.append(Spacer(1, 6))
        story.append(Paragraph("AI-Generated Wellness Reflection", h1_style))
        story.append(Paragraph(
            "The following reflection was generated by an AI assistant based solely on "
            "aggregate statistics. It is not a clinical assessment.",
            muted_style
        ))
        story.append(Spacer(1, 6))
        # Split paragraphs for proper rendering
        for para in ai_summary.split("\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(para, body_style))
        story.append(Spacer(1, 6))

    # ── Selected journal titles (no content) ──
    if selected_journal_titles:
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Journal Entries Referenced", h1_style))
        story.append(Paragraph(
            "The following journal entry titles were included by the user. "
            "Journal content is private and is not included in this report.",
            muted_style
        ))
        for title in selected_journal_titles:
            story.append(Paragraph(f"• {title}", body_style))
        story.append(Spacer(1, 6))

    # ── Footer disclaimer ──
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"⚠️  {DISCLAIMER_TEXT}",
        disclaimer_style
    ))
    story.append(Paragraph(
        "MindReflect AI — Wellness Reflection & Behavioral Pattern Awareness Tool",
        muted_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
