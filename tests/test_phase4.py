"""
tests/test_phase4.py
─────────────────────
Tests for Phase 4 PDF generation.
"""

import sys
import os
import pytest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_pdf_generator_importable():
    from reports.pdf_generator import generate_pdf
    assert callable(generate_pdf)


def test_pdf_generator_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr("config.settings.REPORTS_DIR", str(tmp_path))

    import importlib
    import reports.pdf_generator as pg
    importlib.reload(pg)

    sample_output = """
    ## Company Overview
    Test company overview text.

    ## Technology Stack
    - React
    - Cloudflare

    ## Decision Makers
    | Name | Title |
    |------|-------|
    | John Doe | CEO |

    ## Opportunities
    1. Opportunity one description.

    Subject: Test email subject
    Hi John,
    This is the email body.
    Best,
    Test
    """

    pdf_path = pg.generate_pdf("TestCompany", sample_output)
    assert Path(pdf_path).exists()
    assert pdf_path.endswith(".pdf")


def test_pdf_generator_handles_full_width_lines(tmp_path, monkeypatch):
    monkeypatch.setattr("config.settings.REPORTS_DIR", str(tmp_path))

    import importlib
    import reports.pdf_generator as pg
    importlib.reload(pg)

    pdf = pg.SalesReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=12, top=14, right=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)

    line = "a"
    while pdf.get_string_width(line) < pdf.epw:
        line += "a"
    line = line[:-1]

    sample_output = f"""
    ## Company Overview
    {line}
    Second line after a full-width row.

    ## Technology Stack
    - React
    """

    pdf_path = pg.generate_pdf("WidthTest", sample_output)
    assert Path(pdf_path).exists()


def test_pdf_generator_handles_empty_input(tmp_path, monkeypatch):
    monkeypatch.setattr("config.settings.REPORTS_DIR", str(tmp_path))

    import importlib
    import reports.pdf_generator as pg
    importlib.reload(pg)

    pdf_path = pg.generate_pdf("EmptyTest", "")
    assert Path(pdf_path).exists()