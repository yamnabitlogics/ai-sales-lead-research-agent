import sqlite3
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_settings_importable():
    from config.settings import DB_PATH, REPORTS_DIR, LLM_PROVIDER
    assert DB_PATH
    assert REPORTS_DIR
    assert LLM_PROVIDER in ("anthropic", "openai")


def test_db_init_creates_tables(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("config.settings.DB_PATH", db_file)

    import importlib
    import database.db_manager as dbm
    importlib.reload(dbm)

    dbm.init_db()

    conn = sqlite3.connect(db_file)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()

    assert {"companies", "decision_makers", "opportunities",
            "outreach_emails", "reports"} <= tables


def test_save_and_fetch_company(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("config.settings.DB_PATH", db_file)

    import importlib
    import database.db_manager as dbm
    importlib.reload(dbm)

    dbm.init_db()
    cid = dbm.save_company(
        name="Acme Corp",
        website="https://acme.example.com",
        industry="SaaS",
        tech_stack=["Python", "React"],
    )
    assert isinstance(cid, int) and cid > 0

    company = dbm.fetch_company(cid)
    assert company["name"] == "Acme Corp"
    assert company["industry"] == "SaaS"


def test_all_agents_defined():
    from agents.definitions import (
        coordinator_agent, research_agent, technology_agent,
        decision_maker_agent, opportunity_agent, email_agent, report_agent,
    )
    agents = [
        coordinator_agent, research_agent, technology_agent,
        decision_maker_agent, opportunity_agent, email_agent, report_agent,
    ]
    for agent in agents:
        assert agent.role


def test_build_tasks_returns_six_tasks():
    from agents.tasks import build_tasks
    tasks = build_tasks("TestCo", "https://testco.com")
    assert len(tasks) == 6


def test_tasks_have_descriptions():
    from agents.tasks import build_tasks
    for task in build_tasks("TestCo", "https://testco.com"):
        assert task.description.strip()
        assert task.expected_output.strip()