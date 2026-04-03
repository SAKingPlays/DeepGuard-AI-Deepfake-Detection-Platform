"""Generate PDF, CSV, and JSON reports from detection results."""
from __future__ import annotations
import os
import csv
import json
import logging
from datetime import datetime
from typing import List
from src.detection.base_detector import DetectionResult
from src.config import REPORTS_DIR, APP_NAME, APP_VERSION

logger = logging.getLogger("deepguard")


class ReportGenerator:
    """Generates detection reports in PDF, CSV, and JSON formats."""

    def __init__(self):
        self.reports_dir = REPORTS_DIR
        os.makedirs(self.reports_dir, exist_ok=True)

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── JSON ─────────────────────────────────────────────────────────
    def export_json(self, results: List[DetectionResult],
                    filename: str = None) -> str:
        if not filename:
            filename = os.path.join(self.reports_dir,
                                    f"report_{self._timestamp()}.json")
        data = {
            "report_meta": {
                "application":   APP_NAME,
                "version":       APP_VERSION,
                "generated_at":  datetime.now().isoformat(),
                "total_files":   len(results),
                "fake_count":    sum(1 for r in results if r.is_fake),
                "real_count":    sum(1 for r in results if not r.is_fake and not r.error),
                "error_count":   sum(1 for r in results if r.error),
            },
            "results": []
        }
        for r in results:
            data["results"].append({
                "filepath":        r.filepath,
                "media_type":      r.media_type,
                "verdict":         r.verdict,
                "is_fake":         r.is_fake,
                "confidence":      round(r.confidence, 4),
                "model_used":      r.model_used,
                "processing_time": round(r.processing_time, 3),
                "analysis":        r.analysis_details,
                "explanation":     r.explanation,
                "error":           r.error,
            })
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON report saved: {filename}")
        return filename

    # ── CSV ──────────────────────────────────────────────────────────
    def export_csv(self, results: List[DetectionResult],
                   filename: str = None) -> str:
        if not filename:
            filename = os.path.join(self.reports_dir,
                                    f"report_{self._timestamp()}.csv")
        fieldnames = [
            "filepath", "media_type", "verdict", "is_fake",
            "confidence_pct", "model_used", "processing_time_s",
            "faces_detected", "explanation", "error"
        ]
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow({
                    "filepath":          r.filepath,
                    "media_type":        r.media_type,
                    "verdict":           r.verdict,
                    "is_fake":           r.is_fake,
                    "confidence_pct":    f"{r.confidence*100:.1f}",
                    "model_used":        r.model_used,
                    "processing_time_s": f"{r.processing_time:.3f}",
                    "faces_detected":    r.analysis_details.get("faces_detected", "N/A"),
                    "explanation":       r.explanation,
                    "error":             r.error or "",
                })
        logger.info(f"CSV report saved: {filename}")
        return filename

    # ── PDF ──────────────────────────────────────────────────────────
    def export_pdf(self, results: List[DetectionResult],
                   filename: str = None) -> str:
        if not filename:
            filename = os.path.join(self.reports_dir,
                                    f"report_{self._timestamp()}.pdf")
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table,
                TableStyle, HRFlowable
            )
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT

            doc = SimpleDocTemplate(
                filename, pagesize=A4,
                leftMargin=20*mm, rightMargin=20*mm,
                topMargin=20*mm, bottomMargin=20*mm
            )

            styles = getSampleStyleSheet()
            _C  = colors.HexColor

            title_style = ParagraphStyle(
                "Title", parent=styles["Heading1"],
                fontSize=22, textColor=_C("#00D4FF"),
                spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica-Bold"
            )
            sub_style = ParagraphStyle(
                "Sub", parent=styles["Normal"],
                fontSize=10, textColor=_C("#8892A4"),
                alignment=TA_CENTER, spaceAfter=8
            )
            h2_style = ParagraphStyle(
                "H2", parent=styles["Heading2"],
                fontSize=13, textColor=_C("#E8EAF0"),
                fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4
            )
            body_style = ParagraphStyle(
                "Body", parent=styles["Normal"],
                fontSize=9, textColor=_C("#8892A4"), spaceAfter=4
            )
            verdict_fake = ParagraphStyle(
                "VF", parent=styles["Normal"],
                fontSize=12, textColor=_C("#FF3D57"),
                fontName="Helvetica-Bold"
            )
            verdict_real = ParagraphStyle(
                "VR", parent=styles["Normal"],
                fontSize=12, textColor=_C("#00E676"),
                fontName="Helvetica-Bold"
            )

            story = []

            # Header
            story.append(Paragraph(f"🛡 {APP_NAME}", title_style))
            story.append(Paragraph(
                f"Deepfake Detection Report  •  v{APP_VERSION}  •  "
                f"{datetime.now().strftime('%B %d, %Y %H:%M')}",
                sub_style
            ))
            story.append(HRFlowable(width="100%", color=_C("#252D3D"), thickness=1))
            story.append(Spacer(1, 6*mm))

            # Summary table
            fake_c = sum(1 for r in results if r.is_fake and not r.error)
            real_c = sum(1 for r in results if not r.is_fake and not r.error)
            err_c  = sum(1 for r in results if r.error)

            summary_data = [
                ["Metric", "Value"],
                ["Total Files Analyzed", str(len(results))],
                ["FAKE Detected",        str(fake_c)],
                ["REAL / Authentic",     str(real_c)],
                ["Errors",               str(err_c)],
                ["Detection Rate",
                 f"{100*fake_c/max(1,len(results)-err_c):.1f}%"],
            ]
            tbl = Table(summary_data, colWidths=[90*mm, 60*mm])
            tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), _C("#1A1E2A")),
                ("TEXTCOLOR",     (0, 0), (-1, 0), _C("#00D4FF")),
                ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, 0), 10),
                ("BACKGROUND",    (0, 1), (-1, -1), _C("#0D0F14")),
                ("TEXTCOLOR",     (0, 1), (-1, -1), _C("#E8EAF0")),
                ("FONTSIZE",      (0, 1), (-1, -1), 9),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1),
                 [_C("#0D0F14"), _C("#141720")]),
                ("GRID",          (0, 0), (-1, -1), 0.5, _C("#252D3D")),
                ("ALIGN",         (1, 0), (1, -1), "CENTER"),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 8*mm))

            # Individual results
            story.append(Paragraph("Individual File Results", h2_style))
            story.append(HRFlowable(width="100%", color=_C("#252D3D"), thickness=0.5))
            story.append(Spacer(1, 4*mm))

            for i, r in enumerate(results, 1):
                v_style = verdict_fake if r.is_fake else verdict_real
                story.append(Paragraph(
                    f"{i}. {os.path.basename(r.filepath)}  "
                    f"[{r.media_type.upper()}]  →  {r.verdict}",
                    v_style
                ))

                detail_rows = [
                    ["Confidence",     f"{r.confidence*100:.1f}%"],
                    ["Model",          r.model_used or "N/A"],
                    ["Processing",     f"{r.processing_time:.2f}s"],
                    ["File Path",      r.filepath],
                ]
                for k, v in list(r.analysis_details.items())[:6]:
                    detail_rows.append([k.replace("_", " ").title(), str(v)])

                dtbl = Table(detail_rows, colWidths=[60*mm, 110*mm])
                dtbl.setStyle(TableStyle([
                    ("BACKGROUND",  (0, 0), (0, -1), _C("#141720")),
                    ("TEXTCOLOR",   (0, 0), (0, -1), _C("#8892A4")),
                    ("TEXTCOLOR",   (1, 0), (1, -1), _C("#E8EAF0")),
                    ("FONTSIZE",    (0, 0), (-1, -1), 8),
                    ("GRID",        (0, 0), (-1, -1), 0.3, _C("#252D3D")),
                    ("TOPPADDING",  (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING",(0,0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(Spacer(1, 2*mm))
                story.append(dtbl)

                if r.explanation:
                    story.append(Spacer(1, 2*mm))
                    story.append(Paragraph(
                        f"<i>AI Analysis: {r.explanation}</i>", body_style))

                story.append(Spacer(1, 4*mm))
                story.append(HRFlowable(width="100%", color=_C("#1F2535"), thickness=0.3))
                story.append(Spacer(1, 3*mm))

            doc.build(story)
            logger.info(f"PDF report saved: {filename}")
            return filename

        except ImportError:
            logger.warning("reportlab not installed – falling back to JSON")
            return self.export_json(results, filename.replace(".pdf", ".json"))
        except Exception as e:
            logger.error(f"PDF generation error: {e}", exc_info=True)
            raise
