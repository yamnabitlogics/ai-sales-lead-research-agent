"""
reports/pdf_generator.py
─────────────────────────
Converts the crew's final Markdown output into a
formatted PDF report saved to reports/output/
"""

from fpdf import FPDF
from fpdf.enums import WrapMode, XPos, YPos
from pathlib import Path
from datetime import datetime
from config.settings import REPORTS_DIR
import re


class SalesReportPDF(FPDF):

    def _content_width(self) -> float:
        return self.epw

    def _multi_line(self, text: str, h: float = 6, fill: bool = False) -> None:
        """Render wrapped text and reset x to the left margin for the next line."""
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
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(31, 78, 121)
        self.cell(0, 8, "AI Sales Lead Research Agent - Confidential Report", align="C")
        self.ln(4)
        self.set_draw_color(31, 78, 121)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()} | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C")

    def cover_section(self, company_name: str):
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(31, 78, 121)
        self.ln(10)
        self.cell(0, 12, _sanitize_text(company_name), align="C", new_x=XPos.LMARGIN)
        self.ln(8)
        self.set_font("Helvetica", "", 13)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, "Sales Lead Research Report", align="C")
        self.ln(6)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, datetime.now().strftime("%B %d, %Y"), align="C")
        self.ln(12)
        self.set_draw_color(173, 185, 202)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)

    def section_title(self, title: str):
        self.ln(6)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(31, 78, 121)
        self.set_fill_color(235, 241, 248)
        self.cell(0, 9, f"  {title}", fill=True)
        self.ln(6)
        self.set_text_color(50, 50, 50)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(60, 60, 60)
        self._multi_line(text, h=6)
        self.ln(2)

    def bullet_item(self, text: str):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(60, 60, 60)
        self._multi_line(f"  - {text}", h=5)

    def sub_heading(self, text: str):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(15, 52, 96)
        self.ln(3)
        self.cell(0, 7, text, new_x=XPos.LMARGIN)
        self.ln(5)


def _sanitize_text(text: str) -> str:
    """Replace characters outside Helvetica/latin-1 range."""
    text = text.replace("\u2014", "-")
    text = text.replace("\u2013", "-")
    text = text.replace("\u2018", "'")
    text = text.replace("\u2019", "'")
    text = text.replace("\u201c", '"')
    text = text.replace("\u201d", '"')
    text = text.replace("\u2022", "-")
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _clean_markdown(text: str) -> str:
    """Strip markdown symbols for plain PDF text."""
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"---+", "", text)
    return _sanitize_text(text.strip())


def _parse_sections(raw_output: str) -> dict:
    """
    Split the raw crew output into named sections.
    Looks for common headings the agents produce.
    """
    sections = {
        "overview":       "",
        "tech_stack":     "",
        "decision_makers": "",
        "opportunities":  "",
        "email":          "",
    }

    current = "overview"
    lines = raw_output.split("\n")

    for line in lines:
        lower = line.lower()
        if any(k in lower for k in ["tech stack", "technology", "infrastructure"]):
            current = "tech_stack"
        elif any(k in lower for k in ["decision maker", "leadership", "contact"]):
            current = "decision_makers"
        elif any(k in lower for k in ["opportunit", "pain point", "solution"]):
            current = "opportunities"
        elif any(k in lower for k in ["subject:", "dear ", "hi ", "outreach", "email"]):
            current = "email"
        else:
            sections[current] += line + "\n"

    return sections


def generate_pdf(company_name: str, raw_output: str) -> str:
    """
    Generate a PDF report from the crew's raw output.
    Returns the file path of the saved PDF.
    """
    out_dir = Path(REPORTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^\w\-]", "_", company_name.lower())
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename   = f"{safe_name}_{timestamp}_report.pdf"
    filepath   = out_dir / filename

    pdf = SalesReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=12, top=14, right=12)
    pdf.add_page()

    # Cover
    pdf.cover_section(company_name)

    # Parse sections
    sections = _parse_sections(raw_output)

    # 1. Company Overview
    pdf.section_title("1. Company Overview")
    lines = [l for l in sections["overview"].split("\n") if l.strip()]
    for line in lines:
        clean = _clean_markdown(line)
        if not clean:
            continue
        if line.startswith("#"):
            pdf.sub_heading(clean)
        elif line.strip().startswith(("-", "*", "•")):
            pdf.bullet_item(clean.lstrip("-*• "))
        else:
            pdf.body_text(clean)

    # 2. Technology Stack
    pdf.section_title("2. Technology Stack")
    lines = [l for l in sections["tech_stack"].split("\n") if l.strip()]
    for line in lines:
        clean = _clean_markdown(line)
        if not clean:
            continue
        if line.strip().startswith(("-", "*", "•")):
            pdf.bullet_item(clean.lstrip("-*• "))
        else:
            pdf.body_text(clean)

    # 3. Decision Makers
    pdf.section_title("3. Key Decision Makers")
    lines = [l for l in sections["decision_makers"].split("\n") if l.strip()]
    for line in lines:
        clean = _clean_markdown(line)
        if not clean:
            continue
        if "|" in line:
            # table row - render as bullet
            cols = [c.strip() for c in line.split("|") if c.strip() and "---" not in c]
            if cols:
                pdf.bullet_item("  |  ".join(cols))
        elif line.strip().startswith(("-", "*", "•")):
            pdf.bullet_item(clean.lstrip("-*• "))
        else:
            pdf.body_text(clean)

    # 4. Opportunities
    pdf.section_title("4. Business Opportunities")
    lines = [l for l in sections["opportunities"].split("\n") if l.strip()]
    for line in lines:
        clean = _clean_markdown(line)
        if not clean:
            continue
        if re.match(r"^\d+\.", line.strip()):
            pdf.sub_heading(clean)
        elif line.strip().startswith(("-", "*", "•")):
            pdf.bullet_item(clean.lstrip("-*• "))
        else:
            pdf.body_text(clean)

    # 5. Outreach Email
    pdf.section_title("5. Personalized Outreach Email")
    pdf.set_fill_color(245, 247, 250)
    lines = [l for l in sections["email"].split("\n") if l.strip()]
    for line in lines:
        clean = _clean_markdown(line)
        if not clean:
            continue
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf._multi_line(clean, h=6, fill=True)
        pdf.ln(1)

    pdf.output(str(filepath))
    print(f"PDF saved -> {filepath}")
    return str(filepath)