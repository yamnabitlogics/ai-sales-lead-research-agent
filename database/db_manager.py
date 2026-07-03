import sqlite3
import json
from pathlib import Path
from config.settings import DB_PATH


def get_connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            website     TEXT,
            industry    TEXT,
            description TEXT,
            tech_stack  TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS decision_makers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id  INTEGER REFERENCES companies(id),
            name        TEXT,
            title       TEXT,
            email       TEXT,
            linkedin_url TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS opportunities (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id  INTEGER REFERENCES companies(id),
            description TEXT,
            priority    TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS outreach_emails (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id  INTEGER REFERENCES companies(id),
            subject     TEXT,
            body        TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS reports (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id  INTEGER REFERENCES companies(id),
            file_path   TEXT,
            format      TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );
    """)

    conn.commit()
    conn.close()
    print("Database ready at:", DB_PATH)


def save_company(name, website="", industry="", description="", tech_stack=None, created_at=None):
    conn = get_connection()
    cursor = conn.cursor()
    if created_at:
        cursor.execute(
            """INSERT INTO companies (name, website, industry, description, tech_stack, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, website, industry, description, json.dumps(tech_stack or []), created_at),
        )
    else:
        cursor.execute(
            """INSERT INTO companies (name, website, industry, description, tech_stack)
               VALUES (?, ?, ?, ?, ?)""",
            (name, website, industry, description, json.dumps(tech_stack or [])),
        )
    company_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return company_id


def update_company(company_id, **fields):
    allowed = {"name", "website", "industry", "description", "tech_stack"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    if "tech_stack" in updates and not isinstance(updates["tech_stack"], str):
        updates["tech_stack"] = json.dumps(updates["tech_stack"])
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [company_id]
    conn = get_connection()
    conn.execute(f"UPDATE companies SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def save_decision_maker(company_id, name, title="", email="", linkedin_url=""):
    conn = get_connection()
    conn.execute(
        """INSERT INTO decision_makers (company_id, name, title, email, linkedin_url)
           VALUES (?, ?, ?, ?, ?)""",
        (company_id, name, title, email, linkedin_url),
    )
    conn.commit()
    conn.close()


def save_decision_makers_bulk(company_id, makers: list[dict]):
    conn = get_connection()
    conn.execute("DELETE FROM decision_makers WHERE company_id = ?", (company_id,))
    for m in makers:
        conn.execute(
            """INSERT INTO decision_makers (company_id, name, title, email, linkedin_url)
               VALUES (?, ?, ?, ?, ?)""",
            (
                company_id,
                m.get("name", ""),
                m.get("title", ""),
                m.get("email", ""),
                m.get("linkedin", m.get("linkedin_url", "")),
            ),
        )
    conn.commit()
    conn.close()


def save_opportunity(company_id, description, priority="medium"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO opportunities (company_id, description, priority) VALUES (?, ?, ?)",
        (company_id, description, priority),
    )
    conn.commit()
    conn.close()


def save_opportunities_bulk(company_id, opportunities: list[dict]):
    conn = get_connection()
    conn.execute("DELETE FROM opportunities WHERE company_id = ?", (company_id,))
    for i, opp in enumerate(opportunities):
        description = json.dumps(opp) if isinstance(opp, dict) else str(opp)
        priority = "high" if i == 0 else "medium"
        conn.execute(
            "INSERT INTO opportunities (company_id, description, priority) VALUES (?, ?, ?)",
            (company_id, description, priority),
        )
    conn.commit()
    conn.close()


def save_email(company_id, subject, body):
    conn = get_connection()
    conn.execute("DELETE FROM outreach_emails WHERE company_id = ?", (company_id,))
    conn.execute(
        "INSERT INTO outreach_emails (company_id, subject, body) VALUES (?, ?, ?)",
        (company_id, subject, body),
    )
    conn.commit()
    conn.close()


def save_report(company_id, file_path, fmt="markdown", created_at=None):
    conn = get_connection()
    if created_at:
        conn.execute(
            "INSERT INTO reports (company_id, file_path, format, created_at) VALUES (?, ?, ?, ?)",
            (company_id, file_path, fmt, created_at),
        )
    else:
        conn.execute(
            "INSERT INTO reports (company_id, file_path, format) VALUES (?, ?, ?)",
            (company_id, file_path, fmt),
        )
    conn.commit()
    conn.close()


def fetch_company(company_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


def fetch_company_details(company_id):
    """Return full structured data for a past research run."""
    company = fetch_company(company_id)
    if not company:
        return None

    conn = get_connection()
    makers = conn.execute(
        "SELECT name, title, email, linkedin_url FROM decision_makers WHERE company_id = ?",
        (company_id,),
    ).fetchall()
    opps = conn.execute(
        "SELECT description, priority FROM opportunities WHERE company_id = ? ORDER BY id",
        (company_id,),
    ).fetchall()
    email_row = conn.execute(
        "SELECT subject, body FROM outreach_emails WHERE company_id = ? ORDER BY id DESC LIMIT 1",
        (company_id,),
    ).fetchone()
    conn.close()

    tech_stack = []
    if company.get("tech_stack"):
        try:
            tech_stack = json.loads(company["tech_stack"])
        except json.JSONDecodeError:
            tech_stack = []

    opportunities = []
    for row in opps:
        try:
            opportunities.append(json.loads(row["description"]))
        except (json.JSONDecodeError, TypeError):
            opportunities.append({
                "title": f"Opportunity {len(opportunities) + 1}",
                "summary": row["description"],
                "pain_point": "",
                "solution": "",
                "impact": "",
            })

    email_body = email_row["body"] if email_row else ""
    email_subject = email_row["subject"] if email_row else ""

    return {
        "company_id": company_id,
        "company_name": company["name"],
        "website": company.get("website") or "",
        "date": company.get("created_at"),
        "overview": company.get("description") or "",
        "tech_stack": tech_stack,
        "decision_makers": [
            {
                "name": m["name"],
                "title": m["title"] or "",
                "email": m["email"] or "",
                "linkedin": m["linkedin_url"] or "",
            }
            for m in makers
        ],
        "opportunities": opportunities,
        "email": email_body,
        "email_subject": email_subject,
        "pdf_url": f"/report/{company_id}",
    }


def fetch_history(limit=50):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            c.id,
            c.name,
            c.website,
            c.created_at,
            (
                SELECT file_path FROM reports
                WHERE company_id = c.id AND format = 'pdf'
                ORDER BY id DESC LIMIT 1
            ) AS pdf_path
        FROM companies c
        ORDER BY c.created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_pdf_report_path(company_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT file_path FROM reports
        WHERE company_id = ? AND format = 'pdf'
        ORDER BY id DESC LIMIT 1
        """,
        (company_id,),
    ).fetchone()
    conn.close()
    return row["file_path"] if row else None


if __name__ == "__main__":
    init_db()
