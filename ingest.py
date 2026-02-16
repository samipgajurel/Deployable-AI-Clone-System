import pandas as pd
from db import connect, is_postgres

def run_ingest(csv_path):
    df = pd.read_csv(csv_path)
    df = df[df["Intern Name"].notna()]

    conn = connect()
    cur = conn.cursor()

    # Clear old data first
    cur.execute("DELETE FROM rag_records")
    cur.execute("DELETE FROM supervisor_feedback")
    cur.execute("DELETE FROM interns")

    # ✅ Placeholders depend on DB
    if is_postgres():
        ph = "%s"
    else:
        ph = "?"

    insert_intern_sql = f"""
        INSERT INTO interns(
            id_info, name, email, learning_skill, working_on_project,
            progress_month1, knowledge_gained, progress_rating_num
        )
        VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})
    """

    insert_rag_sql = f"""
        INSERT INTO rag_records(intern_id_info, record_type, text)
        VALUES ({ph},{ph},{ph})
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
            float(rating),
        ))

        text = f"{r.get('Intern Name','')} working on {r.get('Working On Project','')} learned {r.get('Knowledge Gained','')}"
        cur.execute(insert_rag_sql, (
            str(r.get("ID Info", "")).strip(),
            "dataset",
            text,
        ))

    conn.commit()
    conn.close()
    return len(df)
