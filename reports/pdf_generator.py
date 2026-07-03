"""
reports/pdf_generator.py
─────────────────────────
Premium-styled PDF reports for client demos.
"""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import Align, MethodReturnValue, WrapMode, XPos, YPos

from config.settings import REPORTS_DIR
from config.dates import ReportTimestamp
from reports.section_parser import (
    parse_sections,
    parse_tech_stack,
    parse_decision_makers,
    parse_opportunities,
    parse_email,
    _clean_markdown,
)

# Brand palette
NAVY = (15, 31, 61)
NAVY_MID = (26, 54, 93)
ACCENT = (59, 130, 246)
ACCENT_LIGHT = (219, 234, 254)
SLATE = (71, 85, 105)
LIGHT_BG = (248, 250, 252)
WHITE = (255, 255, 255)
SUCCESS = (16, 185, 129)
MUTED = (148, 163, 184)


class SalesReportPDF(FPDF):
    def __init__(self, report_ts: ReportTimestamp, company_name: str, website: str = ""):
        super().__init__()
        self.report_ts = report_ts
        self.company_name = company_name
        self.website = website

    def _content_width(self) -> float:
        return self.epw

    def _multi_line(self, text: str, h: float = 6, fill: bool = False, color: tuple = SLATE) -> None:
        self.set_text_color(*color)
        self.multi_cell(
            self._content_width(),
            h,
            text,
            fill=fill,
            wrapmode=WrapMode.CHAR,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 14, style="F")
        self.set_xy(12, 4)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*WHITE)
        self.cell(0, 6, _sanitize_text(self.company_name), align="L")
        self.set_xy(-60, 4)
        self.cell(48, 6, "CONFIDENTIAL", align="R")
        self.ln(10)

    def footer(self):
        self.set_y(-12)
        self.set_draw_color(*ACCENT_LIGHT)
        self.set_line_width(0.3)
        self.line(12, self.get_y(), 198, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        footer_text = (
            f"AI Sales Lead Research Agent  |  {self.report_ts.footer}  |  "
            f"Page {self.page_no()}"
        )
        self.cell(0, 5, footer_text, align="C")

    def _draw_cover(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 90, style="F")
        self.set_fill_color(*ACCENT)
        self.rect(0, 88, 210, 3, style="F")

        self.set_xy(12, 28)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*ACCENT_LIGHT)
        self.cell(0, 5, "AI SALES LEAD RESEARCH AGENT", align="L")

        self.set_xy(12, 40)
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(*WHITE)
        self._multi_line(_sanitize_text(self.company_name), h=12, color=WHITE)

        self.set_xy(12, 62)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(200, 210, 230)
        subtitle = "Sales Intelligence Report"
        if self.website:
            subtitle += f"  |  {self.website}"
        self.cell(0, 6, _sanitize_text(subtitle))

        self.set_xy(12, 74)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*MUTED)
        self.cell(0, 5, self.report_ts.display_long)

        self.set_y(105)

    def _info_box(self, label: str, value: str):
        self.set_fill_color(*LIGHT_BG)
        self.set_draw_color(226, 232, 240)
        y = self.get_y()
        self.rect(12, y, self.epw, 14, style="FD")
        self.set_xy(16, y + 3)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*MUTED)
        self.cell(40, 4, label.upper())
        self.set_xy(16, y + 8)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*NAVY)
        self.cell(0, 5, _sanitize_text(value))
        self.set_y(y + 18)

    def section_title(self, number: int, title: str):
        if self.get_y() > 250:
            self.add_page()
        self.ln(4)
        y = self.get_y()
        self.set_fill_color(*ACCENT)
        self.rect(12, y, 6, 10, style="F")
        self.set_fill_color(*LIGHT_BG)
        self.rect(18, y, self.epw - 6, 10, style="F")
        self.set_xy(22, y + 2.5)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*NAVY)
        self.cell(0, 6, f"{number}. {title}")
        self.ln(12)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 10)
        self._multi_line(_sanitize_text(text), h=5.5)
        self.ln(2)

    def bullet_item(self, text: str, indent: int = 0):
        self.set_font("Helvetica", "", 9)
        indent_x = self.l_margin + (indent * 5)
        content_x = indent_x + 5
        y = self.get_y()

        # A small drawn dot instead of a ">" character reads as an actual
        # bullet rather than a terminal prompt / markdown blockquote.
        self.set_fill_color(*ACCENT)
        self.ellipse(indent_x + 1, y + 2, 1.6, 1.6, style="F")

        self.set_xy(content_x, y)
        self.set_text_color(*SLATE)
        self.multi_cell(
            self.w - self.r_margin - content_x,
            5,
            _sanitize_text(text),
            wrapmode=WrapMode.CHAR,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.set_x(self.l_margin)

    def sub_heading(self, text: str):
        self.ln(2)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*NAVY_MID)
        self._multi_line(_sanitize_text(text), h=6, color=NAVY_MID)
        self.ln(1)

    def render_tech_tags(self, items: list[str]):
        if not items:
            self.body_text("No technologies detected from public signals.")
            return
        x_start = self.l_margin
        right_edge = self.w - self.r_margin
        bottom_limit = self.h - self.b_margin
        x = x_start
        y = self.get_y()
        row_h = 8
        self.set_font("Helvetica", "", 8)
        for item in items:
            label = _sanitize_text(item)
            w = self.get_string_width(label) + 8

            # Wrap to next row if this tag doesn't fit horizontally
            if x + w > right_edge:
                x = x_start
                y += row_h + 2

            # If the row itself doesn't fit vertically, start a new page
            # and reset BOTH x and y from self.get_y() so the local
            # counters stay in sync with FPDF's actual cursor. This is
            # the fix: previously y was a stale local variable that
            # never got resynced after a page break, causing every
            # subsequent tag to immediately trigger another page break.
            if y + row_h > bottom_limit:
                self.add_page()
                x = x_start
                y = self.get_y()

            self.set_fill_color(*ACCENT_LIGHT)
            self.set_draw_color(*ACCENT)
            self.rect(x, y, w, row_h, style="FD")
            self.set_xy(x + 4, y + 2)
            self.set_text_color(30, 64, 175)
            self.cell(w - 8, 4, label)
            x += w + 3
        self.set_y(y + row_h + 4)

    def render_decision_table(self, makers: list[dict]):
        if not makers:
            self.body_text("No decision makers identified from public sources.")
            return

        col_widths = [40, 35, 38, 38, 35]
        headers = ["Name", "Title", "LinkedIn", "Email", "Notes"]
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*NAVY)
        self.set_text_color(*WHITE)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 8, h, border=0, fill=True, align="C")
        self.ln()

        self.set_font("Helvetica", "", 8)
        for row_i, maker in enumerate(makers):
            fill = row_i % 2 == 0
            self.set_fill_color(*(LIGHT_BG if fill else WHITE))
            self.set_text_color(*SLATE)
            linkedin = maker.get("linkedin", "")
            linkedin_display = "Profile" if linkedin else "-"
            values = [
                maker.get("name", ""),
                maker.get("title", ""),
                linkedin_display,
                maker.get("email", "") or "-",
                maker.get("background", "") or "-",
            ]
            for i, val in enumerate(values):
                text = _sanitize_text(str(val))
                if len(text) > 40:
                    text = text[:37] + "..."
                self.cell(col_widths[i], 7, text, border=0, fill=True)
            self.ln()

    def render_opportunity_card(self, index: int, opp: dict):
        title = opp.get("title", f"Opportunity {index}")

        details = []
        if opp.get("pain_point"):
            details.append(f"Pain: {opp['pain_point']}")
        if opp.get("solution"):
            details.append(f"Solution: {opp['solution']}")
        if opp.get("impact"):
            details.append(f"Impact: {opp['impact']}")
        if opp.get("summary") and not details:
            details.append(opp["summary"])

        self.set_font("Helvetica", "", 8)
        detail_text = _sanitize_text("\n".join(details))
        text_width = self.epw - 9
        wrapped_lines = self.multi_cell(
            text_width, 4, detail_text,
            dry_run=True, wrapmode=WrapMode.CHAR,
            output=MethodReturnValue.LINES,
        )
        card_h = 18 + max(1, len(wrapped_lines)) * 4 + 4

        # Now that we know the real height, make sure the whole card
        # fits on the current page before drawing any of it.
        if self.get_y() + card_h > self.h - self.b_margin:
            self.add_page()
        y = self.get_y()

        self.set_fill_color(*ACCENT)
        self.rect(12, y, 3, card_h, style="F")
        self.set_fill_color(*LIGHT_BG)
        self.rect(15, y, self.epw - 3, card_h, style="F")

        self.set_xy(18, y + 3)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*ACCENT)
        self.cell(0, 4, f"OPPORTUNITY {index}")

        self.set_xy(18, y + 8)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*NAVY)
        self.cell(0, 5, _sanitize_text(title))

        self.set_xy(18, y + 14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*SLATE)
        self._multi_line(detail_text, h=4)
        self.set_y(y + card_h + 4)

    def render_email_block(self, email_data: dict):
        self.set_fill_color(*LIGHT_BG)
        y = self.get_y()
        self.rect(12, y, self.epw, 6, style="F")
        self.set_xy(16, y + 1)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*MUTED)
        self.cell(20, 4, "SUBJECT")
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*NAVY)
        subject = email_data.get("subject") or "(No subject)"
        self.cell(0, 4, _sanitize_text(subject))
        self.ln(8)

        self.set_draw_color(226, 232, 240)
        box_y = self.get_y()
        self.set_font("Helvetica", "", 9)
        body = email_data.get("body") or email_data.get("full", "")
        lines = [l for l in body.split("\n") if l.strip()]
        text_width = self.epw - 8

        # Count the ACTUAL wrapped lines each paragraph will take, not
        # just the raw newline count - a single long paragraph can wrap
        # into many visual lines, and the old estimate under-counted
        # that badly, letting text spill past the drawn border.
        total_wrapped_lines = 0
        for line in lines:
            wrapped = self.multi_cell(
                text_width, 5, _sanitize_text(line),
                dry_run=True, wrapmode=WrapMode.CHAR,
                output=MethodReturnValue.LINES,
            )
            total_wrapped_lines += max(1, len(wrapped))
        box_h = max(40, total_wrapped_lines * 5 + 10)

        # Keep the whole email box on one page rather than letting the
        # border get drawn on one page and the text flow onto the next.
        if box_y + box_h > self.h - self.b_margin:
            self.add_page()
            box_y = self.get_y()

        self.rect(12, box_y, self.epw, box_h, style="D")
        self.set_xy(16, box_y + 5)
        self.set_text_color(*SLATE)
        for line in lines:
            self._multi_line(_sanitize_text(line), h=5)
        self.set_y(box_h + box_y + 4)


def _sanitize_text(text: str) -> str:
    text = str(text or "")
    text = text.replace("\u2014", "-")
    text = text.replace("\u2013", "-")
    text = text.replace("\u2018", "'")
    text = text.replace("\u2019", "'")
    text = text.replace("\u201c", '"')
    text = text.replace("\u201d", '"')
    text = text.replace("\u2022", "-")
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _render_overview_section(pdf: SalesReportPDF, text: str):
    lines = [l for l in text.split("\n") if l.strip()]
    if not lines:
        pdf.body_text("No overview available.")
        return
    for line in lines:
        clean = _clean_markdown(line)
        if not clean:
            continue
        if line.strip().startswith("#") or re.match(r"^[A-Z][\w\s&]+$", clean) and len(clean) < 40:
            pdf.sub_heading(clean)
        elif line.strip().startswith(("-", "*", ">")):
            pdf.bullet_item(clean.lstrip("-*> ").strip())
        else:
            pdf.body_text(clean)


def generate_pdf(
    company_name: str,
    raw_output: str,
    report_ts: ReportTimestamp | None = None,
    website: str = "",
) -> str:
    report_ts = report_ts or ReportTimestamp()
    out_dir = Path(REPORTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^\w\-]", "_", company_name.lower())
    filename = f"{safe_name}_{report_ts.filename_stamp}_report.pdf"
    filepath = out_dir / filename

    sections = parse_sections(raw_output)
    tech_items = parse_tech_stack(sections["tech_stack"])
    makers = parse_decision_makers(sections["decision_makers"])
    opportunities = parse_opportunities(sections["opportunities"])
    email_data = parse_email(sections["email"])

    pdf = SalesReportPDF(report_ts, company_name, website)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(left=12, top=16, right=12)
    pdf.add_page()

    pdf._draw_cover()
    pdf._info_box("Report Date", report_ts.display_long)
    pdf._info_box("Company", company_name)
    if website:
        pdf._info_box("Website", website)
    pdf.ln(4)

    pdf.section_title(1, "Company Overview")
    _render_overview_section(pdf, sections["overview"])

    pdf.section_title(2, "Technology Stack")
    pdf.render_tech_tags(tech_items)

    pdf.section_title(3, "Key Decision Makers")
    pdf.render_decision_table(makers)

    pdf.section_title(4, "Business Opportunities")
    if opportunities:
        for i, opp in enumerate(opportunities, 1):
            pdf.render_opportunity_card(i, opp)
    else:
        pdf.body_text("No specific opportunities identified.")

    pdf.section_title(5, "Personalized Outreach Email")
    pdf.render_email_block(email_data)

    pdf.output(str(filepath))
    print(f"PDF saved -> {filepath}")
    return str(filepath)


# Re-export for app.py backward compatibility
_parse_sections = parse_sections
_clean_markdown = _clean_markdown