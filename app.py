"""
app.py
------
Flask web UI for the AI Sales Lead Research Agent.
Run with: python app.py
"""

import re
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file, abort

from database.db_manager import init_db, fetch_history, get_pdf_report_path
from reports.pdf_generator import _parse_sections, _clean_markdown

app = Flask(__name__)


def _parse_tech_stack(section_text: str) -> list[str]:
    items = []
    for line in section_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        clean = _clean_markdown(line).strip()
        if not clean or clean.lower().startswith("detected technologies"):
            continue
        if clean.startswith(("-", "*", "•")):
            clean = clean.lstrip("-*• ").strip()
        for part in re.split(r"[,;|]", clean):
            part = part.strip()
            if part and part.lower() not in {"none detected", "none"}:
                items.append(part)
    return list(dict.fromkeys(items))


def _parse_decision_makers(section_text: str) -> list[dict]:
    makers = []
    for line in section_text.split("\n"):
        if "|" not in line or "---" in line:
            continue
        cols = [c.strip() for c in line.split("|") if c.strip()]
        if len(cols) >= 2 and cols[0].lower() not in {"name", "full name"}:
            makers.append({
                "name": _clean_markdown(cols[0]),
                "title": _clean_markdown(cols[1]),
                "linkedin": _clean_markdown(cols[2]) if len(cols) > 2 else "",
            })
    if not makers:
        for line in section_text.split("\n"):
            clean = _clean_markdown(line).strip()
            if clean and not clean.lower().startswith(("decision", "leadership", "key")):
                makers.append({"name": clean, "title": "", "linkedin": ""})
    return makers[:5]


def _parse_opportunities(section_text: str) -> list[str]:
    opportunities = []
    for line in section_text.split("\n"):
        clean = _clean_markdown(line).strip()
        if not clean:
            continue
        if re.match(r"^\d+\.", clean):
            opportunities.append(clean)
        elif clean.startswith(("-", "*", "•")):
            opportunities.append(clean.lstrip("-*• ").strip())
    return opportunities[:3]


def _structure_results(raw_output: str) -> dict:
    sections = _parse_sections(raw_output)
    return {
        "overview": _clean_markdown(sections["overview"]).strip(),
        "tech_stack": _parse_tech_stack(sections["tech_stack"]),
        "decision_makers": _parse_decision_makers(sections["decision_makers"]),
        "opportunities": _parse_opportunities(sections["opportunities"]),
        "email": _clean_markdown(sections["email"]).strip(),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/research", methods=["POST"])
def research():
    data = request.get_json(silent=True) or {}
    company = (data.get("company") or "").strip()
    website = (data.get("website") or "").strip()

    if not company:
        return jsonify({"error": "Company name is required."}), 400

    try:
        from main import run_pipeline

        init_db()
        result = run_pipeline(company_name=company, website=website)
        structured = _structure_results(result["raw_output"])
        return jsonify({
            "company_id": result["company_id"],
            "company_name": result["company_name"],
            "website": website,
            "pdf_url": f"/report/{result['company_id']}",
            "overview": structured["overview"],
            "tech_stack": structured["tech_stack"],
            "decision_makers": structured["decision_makers"],
            "opportunities": structured["opportunities"],
            "email": structured["email"],
            "raw_output": result["raw_output"],
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


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
