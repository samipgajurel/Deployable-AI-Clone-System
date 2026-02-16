import os
import sqlite3

def connect():
    # Railway provides DATABASE_URL for Postgres
    if os.getenv("DATABASE_URL"):
        import psycopg2
        from psycopg2.extras import RealDictCursor

        db_url = os.getenv("DATABASE_URL")
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

    # Local fallback
    conn = sqlite3.connect("interns.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = connect()
    cur = conn.cursor()

    # Common schema (works for both; types adjusted)
    if os.getenv("DATABASE_URL"):
        cur.execute("""
        CREATE TABLE IF NOT EXISTS interns(
            id_info TEXT PRIMARY KEY,
            intern_no INTEGER,
            name TEXT,
            email TEXT,
            role TEXT,
            start_date TEXT,
            duration TEXT,
            duration_months DOUBLE PRECISION,
            learning_skill TEXT,
            status TEXT,
            previous_skills TEXT,
            working_on_project TEXT,
            progress_month1 TEXT,
            knowledge_gained TEXT,
            progress_rating_text TEXT,
            progress_rating_num DOUBLE PRECISION,
            environment_review TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS supervisor_feedback(
            feedback_id SERIAL PRIMARY KEY,
            intern_id_info TEXT REFERENCES interns(id_info) ON DELETE CASCADE,
            supervisor_name TEXT,
            note TEXT,
            rating INTEGER,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS rag_records(
            record_id SERIAL PRIMARY KEY,
            intern_id_info TEXT REFERENCES interns(id_info) ON DELETE CASCADE,
            record_type TEXT,
            text TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)
    else:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS interns(
            id_info TEXT PRIMARY KEY,
            intern_no INTEGER,
            name TEXT,
            email TEXT,
            role TEXT,
            start_date TEXT,
            duration TEXT,
            duration_months REAL,
            learning_skill TEXT,
            status TEXT,
            previous_skills TEXT,
            working_on_project TEXT,
            progress_month1 TEXT,
            knowledge_gained TEXT,
            progress_rating_text TEXT,
            progress_rating_num REAL,
            environment_review TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS supervisor_feedback(
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id_info TEXT,
            supervisor_name TEXT,
            note TEXT,
            rating INTEGER,
            created_at TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS rag_records(
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id_info TEXT,
            record_type TEXT,
            text TEXT,
            created_at TEXT
        )
        """)

    conn.commit()
    conn.close()
