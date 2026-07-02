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


def save_company(name, website="", industry="", description="", tech_stack=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO companies (name, website, industry, description, tech_stack)
           VALUES (?, ?, ?, ?, ?)""",
        (name, website, industry, description, json.dumps(tech_stack or []))
    )
    company_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return company_id


def save_decision_maker(company_id, name, title="", email="", linkedin_url=""):
    conn = get_connection()
    conn.execute(
        """INSERT INTO decision_makers (company_id, name, title, email, linkedin_url)
           VALUES (?, ?, ?, ?, ?)""",
        (company_id, name, title, email, linkedin_url)
    )
    conn.commit()
    conn.close()


def save_opportunity(company_id, description, priority="medium"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO opportunities (company_id, description, priority) VALUES (?, ?, ?)",
        (company_id, description, priority)
    )
    conn.commit()
    conn.close()


def save_email(company_id, subject, body):
    conn = get_connection()
    conn.execute(
        "INSERT INTO outreach_emails (company_id, subject, body) VALUES (?, ?, ?)",
        (company_id, subject, body)
    )
    conn.commit()
    conn.close()


def save_report(company_id, file_path, fmt="markdown"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO reports (company_id, file_path, format) VALUES (?, ?, ?)",
        (company_id, file_path, fmt)
    )
    conn.commit()
    conn.close()


def fetch_company(company_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


def fetch_history(limit=50):
    """Return past researched companies with PDF report links."""
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