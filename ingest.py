import pandas as pd
from db import connect

def run_ingest(csv_path):
    df = pd.read_csv(csv_path)
    df = df[df["Intern Name"].notna()]

    conn = connect()
    cur = conn.cursor()

    # Clear old data first
    cur.execute("DELETE FROM rag_records")
    cur.execute("DELETE FROM supervisor_feedback")
    cur.execute("DELETE FROM interns")

    insert_intern_sql = """
        INSERT INTO interns(
            id_info, name, email, learning_skill, working_on_project,
            progress_month1, knowledge_gained, progress_rating_num
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """

    insert_rag_sql = """
        INSERT INTO rag_records(intern_id_info, record_type, text)
        VALUES (%s,%s,%s)
    """

    for _, r in df.iterrows():
        rating = str(r.get("Progress Rating", "")).count("★")

        cur.execute(insert_intern_sql, (
            str(r.get("ID Info", "")).strip(),
            str(r.get("Intern Name", "")).strip(),
            str(r.get("E-mail", "")).strip(),
            str(r.get("Learning Skill (Internship)", "")).strip(),
            str(r.get("Working On Project", "")).strip(),
            str(r.get("Progress (1st months)", "")).strip(),
            str(r.get("Knowledge Gained", "")).strip(),
            rating
        ))

        text = f"{r['Intern Name']} working on {r['Working On Project']} learned {r['Knowledge Gained']}"
        cur.execute(insert_rag_sql, (
            str(r.get("ID Info", "")).strip(),
            "dataset",
            text
        ))

    # Commit ONCE (important for Postgres)
    conn.commit()
    conn.close()

    return len(df)
