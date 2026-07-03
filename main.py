import argparse
import re
import threading
from pathlib import Path

from crewai import Crew, Process

from config.dates import ReportTimestamp
from config.settings import VERBOSE, REPORTS_DIR
from config.logger import get_logger
from agents.definitions import (
    research_agent,
    technology_agent,
    decision_maker_agent,
    opportunity_agent,
    email_agent,
    report_agent,
)
from agents.tasks import build_tasks
from database.db_manager import (
    init_db,
    save_company,
    save_report,
    save_decision_makers_bulk,
    save_opportunities_bulk,
    save_email,
    update_company,
)
from pipeline.progress import progress_tracker, AGENT_STEPS
from reports.pdf_generator import generate_pdf
from reports.section_parser import structure_results, validate_structured_results
from utils.errors import PipelineError
from utils.validation import (
    normalize_website,
    validate_company_name,
    validate_api_configuration,
)

logger = get_logger("main")


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.strip().lower())


def _save_markdown_report(company_name: str, content: str, report_ts: ReportTimestamp) -> str:
    out_dir = Path(REPORTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_filename(company_name)}_{report_ts.filename_stamp}_report.md"
    path = out_dir / filename
    path.write_text(content, encoding="utf-8")
    return str(path)


def _persist_structured_data(company_id: int, structured: dict) -> None:
    update_company(
        company_id,
        description=structured.get("overview", ""),
        tech_stack=structured.get("tech_stack", []),
    )
    save_decision_makers_bulk(company_id, structured.get("decision_makers", []))
    save_opportunities_bulk(company_id, structured.get("opportunities", []))
    email_body = structured.get("email", "")
    email_subject = structured.get("email_subject", "")
    if email_body:
        save_email(company_id, email_subject, email_body)


def run_pipeline(company_name: str, website: str = "", job_id: str | None = None) -> dict:
    company_name = validate_company_name(company_name)
    website = normalize_website(website)
    validate_api_configuration()

    report_ts = ReportTimestamp()

    logger.info(f"Pipeline started for: {company_name} | {website}")
    print(f"\n{'='*60}")
    print(f"  Sales Lead Research Agent")
    print(f"  Company : {company_name}")
    print(f"  Website : {website or 'not provided'}")
    print(f"  Date    : {report_ts.display_long}")
    print(f"{'='*60}\n")

    if job_id:
        progress_tracker.set_message(job_id, "Initializing research pipeline...")

    try:
        init_db()
        tasks = build_tasks(company_name, website, report_ts.display_long)

        completed_tasks = {"count": 0}

        def _task_callback(_output) -> None:
            completed_tasks["count"] += 1
            if job_id and completed_tasks["count"] <= len(AGENT_STEPS) - 1:
                step = AGENT_STEPS[completed_tasks["count"] - 1]
                progress_tracker.advance(job_id, f"{step['label']} complete — {step['detail']}")

        crew = Crew(
            agents=[
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
            task_callback=_task_callback,
        )

        if job_id:
            progress_tracker.set_message(
                job_id,
                f"{AGENT_STEPS[0]['label']} — {AGENT_STEPS[0]['detail']}",
            )

        result = crew.kickoff()
        logger.info("Crew kickoff completed successfully")

        if job_id:
            progress_tracker.advance(job_id, "Finalizing — Saving report and PDF")

        report_text = str(result).strip()
        structured = structure_results(report_text)
        validate_structured_results(structured)

        company_id = save_company(
            name=company_name,
            website=website,
            description=structured["overview"],
            tech_stack=structured["tech_stack"],
            created_at=report_ts.iso,
        )
        _persist_structured_data(company_id, structured)

        report_path = _save_markdown_report(company_name, report_text, report_ts)
        save_report(company_id, report_path, fmt="markdown", created_at=report_ts.iso)

        pdf_path = generate_pdf(
            company_name,
            report_text,
            report_ts=report_ts,
            website=website,
        )
        save_report(company_id, pdf_path, fmt="pdf", created_at=report_ts.iso)

        print(f"\n✅  Pipeline complete!")
        print(f"   Date     → {report_ts.display_long}")
        print(f"   Markdown → {report_path}")
        print(f"   PDF      → {pdf_path}")
        print(f"   DB id    → {company_id}\n")

        return {
            "company_id": company_id,
            "company_name": company_name,
            "website": website,
            "report_date": report_ts.iso,
            "report_date_display": report_ts.display_long,
            "report_path": report_path,
            "pdf_path": pdf_path,
            "raw_output": report_text,
            **structured,
        }

    except PipelineError:
        raise
    except Exception as e:
        logger.error(f"Pipeline failed for {company_name}: {e}", exc_info=True)
        print(f"\n❌  Pipeline failed: {e}")
        raise PipelineError(
            f"Research pipeline failed: {e}",
            code="pipeline_error",
        ) from e


def run_pipeline_async(job_id: str, company_name: str, website: str = "") -> None:
    try:
        result = run_pipeline(company_name, website, job_id=job_id)
        progress_tracker.complete(job_id, result)
    except PipelineError as exc:
        progress_tracker.fail(job_id, exc.message)
    except Exception as exc:
        progress_tracker.fail(job_id, str(exc))


def start_pipeline_job(company_name: str, website: str = "") -> str:
    job_id = progress_tracker.create_job(company_name, website)
    thread = threading.Thread(
        target=run_pipeline_async,
        args=(job_id, company_name, website),
        daemon=True,
    )
    thread.start()
    return job_id


def _parse_args():
    parser = argparse.ArgumentParser(description="AI Sales Lead Research Agent")
    parser.add_argument("--company", required=True, help="Company name to research")
    parser.add_argument("--website", default="", help="Company website URL (optional)")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_pipeline(company_name=args.company, website=args.website)
