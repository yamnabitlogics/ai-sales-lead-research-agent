import argparse
import re
from pathlib import Path
from datetime import datetime

from crewai import Crew, Process

from config.settings import VERBOSE, REPORTS_DIR
from agents.definitions import (
    coordinator_agent,
    research_agent,
    technology_agent,
    decision_maker_agent,
    opportunity_agent,
    email_agent,
    report_agent,
)
from agents.tasks import build_tasks
from database.db_manager import init_db, save_company, save_report


def _safe_filename(name):
    return re.sub(r"[^\w\-]", "_", name.strip().lower())


def _save_markdown_report(company_name, content):
    out_dir = Path(REPORTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_filename(company_name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_report.md"
    path = out_dir / filename
    path.write_text(content, encoding="utf-8")
    return str(path)


def run_pipeline(company_name, website=""):
    print(f"\n{'='*60}")
    print(f"  Sales Lead Research Agent")
    print(f"  Company : {company_name}")
    print(f"  Website : {website or 'not provided'}")
    print(f"  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    init_db()

    tasks = build_tasks(company_name, website)

    crew = Crew(
        agents=[
            coordinator_agent,
            research_agent,
            technology_agent,
            decision_maker_agent,
            opportunity_agent,
            email_agent,
            report_agent,
        ],
        tasks=tasks,
        process=Process.sequential,
        verbose=VERBOSE,
    )

    result = crew.kickoff()

    company_id = save_company(name=company_name, website=website)

    report_text = str(result)
    report_path = _save_markdown_report(company_name, report_text)
    save_report(company_id, report_path, fmt="markdown")

    print(f"\n✅  Pipeline complete!")
    print(f"   Report saved → {report_path}")
    print(f"   DB company_id → {company_id}\n")

    return {
        "company_id": company_id,
        "company_name": company_name,
        "report_path": report_path,
        "raw_output": report_text,
    }


def _parse_args():
    parser = argparse.ArgumentParser(description="AI Sales Lead Research Agent")
    parser.add_argument("--company", required=True, help="Company name to research")
    parser.add_argument("--website", default="", help="Company website URL (optional)")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_pipeline(company_name=args.company, website=args.website)