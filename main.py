import argparse
import re
from pathlib import Path
from datetime import datetime

from crewai import Crew, Process
from reports.pdf_generator import generate_pdf

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
from database.db_manager import (
    init_db, save_company, save_report,
    save_decision_maker, save_opportunity
)
from config.logger import get_logger
logger = get_logger("main")
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
    logger.info(f"Pipeline started for: {company_name} | {website}")
    print(f"\n{'='*60}")
    print(f"  Sales Lead Research Agent")
    print(f"  Company : {company_name}")
    print(f"  Website : {website or 'not provided'}")
    print(f"  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    try:
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
        logger.info("Crew kickoff completed successfully")

        company_id = save_company(name=company_name, website=website)
        save_decision_maker(company_id, name="See report", title="See report")
        save_opportunity(company_id, description="See report for full analysis", priority="high")

        report_text = str(result)

        report_path = _save_markdown_report(company_name, report_text)
        save_report(company_id, report_path, fmt="markdown")
        logger.info(f"Markdown report saved: {report_path}")

        pdf_path = generate_pdf(company_name, report_text)
        save_report(company_id, pdf_path, fmt="pdf")
        logger.info(f"PDF report saved: {pdf_path}")

        print(f"\n✅  Pipeline complete!")
        print(f"   Markdown → {report_path}")
        print(f"   PDF      → {pdf_path}")
        print(f"   DB id    → {company_id}\n")

        return {
            "company_id":   company_id,
            "company_name": company_name,
            "report_path":  report_path,
            "pdf_path":     pdf_path,
            "raw_output":   report_text,
        }

    except Exception as e:
        logger.error(f"Pipeline failed for {company_name}: {e}", exc_info=True)
        print(f"\n❌  Pipeline failed: {e}")
        raise
def _parse_args():
    parser = argparse.ArgumentParser(description="AI Sales Lead Research Agent")
    parser.add_argument("--company", required=True, help="Company name to research")
    parser.add_argument("--website", default="", help="Company website URL (optional)")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_pipeline(company_name=args.company, website=args.website)