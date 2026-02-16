import os
import pandas as pd
import numpy as np
from datetime import datetime
from db import connect

def _sql(sqlite_sql: str) -> str:
    # sqlite uses ?, psycopg2 uses %s
    return sqlite_sql.replace("?", "%s") if os.getenv("DATABASE_URL") else sqlite_sql

def rating_to_num(x):
    if pd.isna(x): 
        return np.nan
    return str(x).count("★")

def clean_csv(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path).replace({"nan": np.nan, "NaN": np.nan, "": np.nan})

    # Keep only INTERN rows with required fields
    for c in ["Intern Name", "E-mail", "ID Info"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().replace({"nan": np.nan})

    df = df[
        df["Intern Name"].notna() &
        df["E-mail"].notna() &
        df["ID Info"].notna() &
        (df["Role"].fillna("").str.lower() == "intern")
    ].copy()

    df["Intern No"] = pd.to_numeric(df["No of Interns"], errors="coerce").astype("Int64")
    df["Start Date"] = pd.to_datetime(df["Start Date"], errors="coerce")
    df["Duration Months"] = df["Duration of Internship"].astype(str).str.extract(r"(\d+)").astype("float")
    df["Progress Rating Num"] = df["Progress Rating"].apply(rating_to_num)

    # Format dates as string
    df["Start Date"] = df["Start Date"].dt.strftime("%Y-%m-%d")

    return df

def upsert_interns(df: pd.DataFrame):
    conn = connect()
    cur = conn.cursor()

    # Clear existing dataset (fresh dataset load)
    cur.execute("DELETE FROM rag_records")
    cur.execute("DELETE FROM supervisor_feedback")
    cur.execute("DELETE FROM interns")

    for _, r in df.iterrows():
        cur.execute(_sql("""
        INSERT INTO interns(
            id_info, intern_no, name, email, role, start_date, duration, duration_months,
            learning_skill, status, previous_skills, working_on_project, progress_month1,
            knowledge_gained, progress_rating_text, progress_rating_num, environment_review
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """), (
            str(r.get("ID Info", "")).strip(),
            int(r["Intern No"]) if pd.notna(r.get("Intern No")) else None,
            str(r.get("Intern Name", "")).strip(),
            str(r.get("E-mail", "")).strip(),
            str(r.get("Role", "")).strip(),
            r.get("Start Date", None),
            r.get("Duration of Internship", None),
            float(r["Duration Months"]) if pd.notna(r.get("Duration Months")) else None,
            r.get("Learning Skill (Internship)", None),
            r.get("Status", None),
            r.get("Previous Skills", None),
            r.get("Working On Project", None),
            r.get("Progress (1st months)", None),
            r.get("Knowledge Gained", None),
            r.get("Progress Rating", None),
            float(r["Progress Rating Num"]) if pd.notna(r.get("Progress Rating Num")) else None,
            r.get("Environment (Review By The Interns)", None),
        ))

    conn.commit()
    conn.close()

def rebuild_rag_records():
    conn = connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM rag_records")

    interns = cur.execute("SELECT * FROM interns").fetchall()
    now = datetime.utcnow().isoformat()

    def add(iid, rtype, text):
        cur.execute(_sql("""
            INSERT INTO rag_records(intern_id_info, record_type, text, created_at)
            VALUES (?,?,?,?)
        """), (iid, rtype, text, now))

    for row in interns:
        iid = row["id_info"]
        name = row["name"]

        add(iid, "profile", f"Intern {name} ({iid}) email={row['email']} learning_skill={row['learning_skill']} status={row['status']} previous_skills={row['previous_skills']}")
        if row.get("working_on_project"):
            add(iid, "project", f"{name} working on project: {row['working_on_project']}")
        if row.get("progress_month1"):
            add(iid, "progress_m1", f"Month-1 progress for {name}: {row['progress_month1']}")
        if row.get("knowledge_gained"):
            add(iid, "knowledge", f"Knowledge gained by {name}: {row['knowledge_gained']}")
        if row.get("progress_rating_text") or row.get("progress_rating_num") is not None:
            add(iid, "rating", f"{name} rating: {row.get('progress_rating_text')} numeric={row.get('progress_rating_num')}")
        if row.get("environment_review"):
            add(iid, "environment", f"Environment review by {name}: {row['environment_review']}")

    conn.commit()
    conn.close()

def run_ingest(csv_path: str):
    df = clean_csv(csv_path)
    upsert_interns(df)
    rebuild_rag_records()
    return len(df)
