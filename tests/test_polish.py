"""
tests/test_polish.py
────────────────────
Tests for polish features: parsing, validation, dates, progress.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_report_timestamp_consistency():
    from config.dates import ReportTimestamp
    from datetime import datetime

    ts = ReportTimestamp(datetime(2026, 7, 3, 14, 30, 0))
    assert ts.iso == "2026-07-03 14:30:00"
    assert ts.display_long == "July 03, 2026"
    assert ts.filename_stamp == "20260703_143000"


def test_normalize_website():
    from utils.validation import normalize_website
    from utils.errors import ValidationError

    assert normalize_website("shopify.com") == "https://shopify.com"
    assert normalize_website("https://shopify.com/") == "https://shopify.com"
    assert normalize_website("") == ""

    with pytest.raises(ValidationError):
        normalize_website("not a url!!!")


def test_parse_opportunities_structured():
    from reports.section_parser import parse_opportunities

    text = """
    ### Opportunity 1: AI Automation
    **Pain Point:** Manual data entry costs 20hrs/week
    **Proposed Solution:** Deploy intelligent document processing
    **Business Impact:** Save $150K annually
    """
    opps = parse_opportunities(text)
    assert len(opps) == 1
    assert opps[0]["title"] == "AI Automation"
    assert "Manual data entry" in opps[0]["pain_point"]
    assert "document processing" in opps[0]["solution"]
    assert "$150K" in opps[0]["impact"]


def test_parse_decision_makers_table():
    from reports.section_parser import parse_decision_makers

    text = """
    | Name | Title | LinkedIn | Email |
    |------|-------|----------|-------|
    | Jane Smith | CTO | https://linkedin.com/in/jane | jane@co.com |
    """
    makers = parse_decision_makers(text)
    assert len(makers) == 1
    assert makers[0]["name"] == "Jane Smith"
    assert makers[0]["title"] == "CTO"
    assert "linkedin.com" in makers[0]["linkedin"]


def test_progress_tracker_lifecycle():
    from pipeline.progress import progress_tracker

    job_id = progress_tracker.create_job("Acme", "https://acme.com")
    status = progress_tracker.get(job_id)
    assert status["status"] == "running"
    assert status["percent"] == 0

    progress_tracker.advance(job_id)
    status = progress_tracker.get(job_id)
    assert status["current_step"] == 1

    progress_tracker.complete(job_id, {"company_id": 1})
    status = progress_tracker.get(job_id)
    assert status["status"] == "complete"
    assert status["percent"] == 100


def test_pdf_uses_consistent_date(tmp_path, monkeypatch):
    monkeypatch.setattr("config.settings.REPORTS_DIR", str(tmp_path))

    from pathlib import Path
    from config.dates import ReportTimestamp
    from datetime import datetime
    import importlib
    import reports.pdf_generator as pg
    importlib.reload(pg)

    ts = ReportTimestamp(datetime(2026, 7, 3, 10, 0, 0))
    sample = "## Company Overview\nTest content.\n"
    path = pg.generate_pdf("DateCo", sample, report_ts=ts, website="https://dateco.com")
    assert Path(path).exists()
    assert "20260703_100000" in path
