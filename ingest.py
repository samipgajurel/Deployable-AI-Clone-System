import pandas as pd
from db import connect, is_postgres

def run_ingest(csv_path):
    df = pd.read_csv(csv_path)

    # Keep only valid intern rows
    df = df[df["Intern Name"].notna()]

    # ✅ Clean ID Info and drop duplicates to avoid unique constraint error
    df["ID Info"] = df["ID Info"].astype(str).str.strip()
    df = df[df["ID Info"].notna() & (df["ID Info"] != "")]
    df = df.drop_duplicates(subset=["ID Info"], keep="first")

    conn = connect()
    cur = conn.cursor()

    # Clear old data first
    cur.execute("DELETE FROM rag_records")
    cur.execute("DELETE FROM supervisor_feedback")
    cur.execute("DELETE FROM interns")

    # ✅ Build DB-specific SQL
    if is_postgres():
        insert_intern_sql = """
            INSERT INTO interns(
                id_info, name, email, learning_skill, working_on_project,
                progress_month1, knowledge_gained, progress_rating_num
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id_info) DO UPDATE SET
                name = EXCLUDED.name,
                email = EXCLUDED.email,
                learning_skill = EXCLUDED.learning_skill,
                working_on_project = EXCLUDED.working_on_project,
                progress_month1 = EXCLUDED.progress_month1,
                knowledge_gained = EXCLUDED.knowledge_gained,
                progress_rating_num = EXCLUDED.progress_rating_num
        """
        insert_rag_sql = """
            INSERT INTO rag_records(intern_id_info, record_type, text)
            VALUES (%s,%s,%s)
        """
    else:
        # SQLite
        insert_intern_sql = """
            INSERT OR REPLACE INTO interns(
                id_info, name, email, learning_skill, working_on_project,
                progress_month1, knowledge_gained, progress_rating_num
            )
            VALUES (?,?,?,?,?,?,?,?)
        """
        insert_rag_sql = """
            INSERT INTO rag_records(intern_id_info, record_type, text)
            VALUES (?,?,?)
        """

    for _, r in df.iterrows():
        rating = str(r.get("Progress Rating", "")).count("★")

        intern_id = str(r.get("ID Info", "")).strip()
        name = str(r.get("Intern Name", "")).strip()

        cur.execute(insert_intern_sql, (
            intern_id,
            name,
            str(r.get("E-mail", "")).strip(),
            str(r.get("Learning Skill (Internship)", "")).strip(),
            str(r.get("Working On Project", "")).strip(),
            str(r.get("Progress (1st months)", "")).strip(),
            str(r.get("Knowledge Gained", "")).strip(),
            float(rating),
        ))

        text = f"{name} working on {r.get('Working On Project','')} learned {r.get('Knowledge Gained','')}"
        cur.execute(insert_rag_sql, (intern_id, "dataset", text))

    conn.commit()
    conn.close()
    return int(len(df))
