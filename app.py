"""
app.py
------
Flask web UI for the AI Sales Lead Research Agent.
Run with: python app.py
"""

from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file, abort

from database.db_manager import init_db, fetch_history, get_pdf_report_path, fetch_company_details
from reports.section_parser import structure_results
from utils.errors import PipelineError
from utils.validation import normalize_website, validate_company_name
from main import start_pipeline_job
from pipeline.progress import progress_tracker

app = Flask(__name__)


def _format_api_error(exc: Exception) -> tuple[dict, int]:
    if isinstance(exc, PipelineError):
        return {"error": exc.message, "code": exc.code}, 400 if exc.code == "validation_error" else 500
    return {"error": str(exc), "code": "pipeline_error"}, 500


def _build_response(result: dict) -> dict:
    return {
        "company_id": result["company_id"],
        "company_name": result["company_name"],
        "website": result.get("website", ""),
        "report_date": result.get("report_date"),
        "report_date_display": result.get("report_date_display"),
        "pdf_url": f"/report/{result['company_id']}",
        "overview": result.get("overview", ""),
        "tech_stack": result.get("tech_stack", []),
        "decision_makers": result.get("decision_makers", []),
        "opportunities": result.get("opportunities", []),
        "email": result.get("email", ""),
        "email_subject": result.get("email_subject", ""),
        "raw_output": result.get("raw_output", ""),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/research", methods=["POST"])
def research():
    data = request.get_json(silent=True) or {}
    try:
        company = validate_company_name(data.get("company"))
        website = normalize_website(data.get("website"))
    except PipelineError as exc:
        return jsonify({"error": exc.message, "code": exc.code}), 400

    init_db()
    job_id = start_pipeline_job(company_name=company, website=website)
    return jsonify({"job_id": job_id}), 202


@app.route("/research/status/<job_id>")
def research_status(job_id):
    status = progress_tracker.get(job_id)
    if not status:
        return jsonify({"error": "Job not found.", "code": "not_found"}), 404
    return jsonify(status)


@app.route("/research/result/<job_id>")
def research_result(job_id):
    status = progress_tracker.get(job_id)
    if not status:
        return jsonify({"error": "Job not found.", "code": "not_found"}), 404
    if status["status"] == "error":
        return jsonify({"error": status["error"], "code": "pipeline_error"}), 500
    if status["status"] != "complete":
        return jsonify({"error": "Job still running.", "code": "in_progress"}), 202

    result = progress_tracker.get_result(job_id)
    if not result:
        return jsonify({"error": "Result not available.", "code": "not_found"}), 404
    return jsonify(_build_response(result))


@app.route("/history")
def history():
    init_db()
    rows = fetch_history()
    return jsonify([
        {
            "id": row["id"],
            "name": row["name"],
            "website": row["website"] or "",
            "date": row["created_at"],
            "report_url": f"/report/{row['id']}" if row.get("pdf_path") else None,
        }
        for row in rows
    ])


@app.route("/company/<int:company_id>")
def company_details(company_id):
    init_db()
    details = fetch_company_details(company_id)
    if not details:
        abort(404, description="Company not found.")
    return jsonify(details)


@app.route("/report/<int:company_id>")
def download_report(company_id):
    init_db()
    pdf_path = get_pdf_report_path(company_id)
    if not pdf_path:
        abort(404, description="Report not found.")
    path = Path(pdf_path)
    if not path.exists():
        abort(404, description="Report file missing on disk.")
    return send_file(path, as_attachment=True, download_name=path.name)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
