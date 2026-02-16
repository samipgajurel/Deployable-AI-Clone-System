from db import connect, is_postgres

def generate_ai_clone(intern_id: str, note: str, supervisor_name: str = "Samip Gajurel", rating: int | None = None):
    conn = connect()
    cur = conn.cursor()

    ph = "%s" if is_postgres() else "?"

    # ---- Get intern ----
    cur.execute(f"SELECT * FROM interns WHERE id_info={ph}", (intern_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return {"error": "Intern not found"}

    # Postgres returns dict (RealDictCursor), SQLite returns sqlite3.Row (dict-like)
    if isinstance(row, dict):
        name = row.get("name")
        working_on_project = row.get("working_on_project")
        knowledge_gained = row.get("knowledge_gained")
        progress_month1 = row.get("progress_month1")
        progress_rating_num = row.get("progress_rating_num")
    else:
        # sqlite Row supports dict-style too, but keep safe fallback
        name = row["name"] if "name" in row.keys() else row[2]
        working_on_project = row["working_on_project"] if "working_on_project" in row.keys() else row[11]
        knowledge_gained = row["knowledge_gained"] if "knowledge_gained" in row.keys() else row[13]
        progress_month1 = row["progress_month1"] if "progress_month1" in row.keys() else row[12]
        progress_rating_num = row["progress_rating_num"] if "progress_rating_num" in row.keys() else row[15]

    # if rating not provided, use stored rating_num if exists
    if rating is None:
        try:
            rating = int(progress_rating_num or 0)
        except Exception:
            rating = 0

    # ---- Get RAG memory ----
    cur.execute(f"SELECT text FROM rag_records WHERE intern_id_info={ph}", (intern_id,))
    rag_rows = cur.fetchall()

    rag_texts = []
    for r in rag_rows or []:
        if isinstance(r, dict):
            rag_texts.append(r.get("text"))
        else:
            # sqlite row / tuple
            try:
                rag_texts.append(r["text"])
            except Exception:
                rag_texts.append(r[0])

    rag_texts = [t for t in rag_texts if t]

    # ---- AI Logic (simple evaluation model) ----
    strengths = []
    weaknesses = []

    if rating >= 4:
        strengths.append("Strong performance")
    elif rating == 3:
        strengths.append("Good progress")
        weaknesses.append("Needs consistency")
    else:
        weaknesses.append("Needs improvement")

    if knowledge_gained:
        strengths.append("Learning actively")

    if note and "documentation" in note.lower():
        weaknesses.append("Documentation lacking")

    action_plan = [
        "Weekly progress reporting",
        "Improve code documentation",
        "Supervisor review every Friday"
    ]

    result = {
        "intern_id": intern_id,
        "intern": name,
        "project": working_on_project,
        "progress_score": rating,
        "current_progress": progress_month1,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "action_plan": action_plan,
        "memory_used": rag_texts
    }

    # ---- Store supervisor feedback ----
    cur.execute(
        f"""
        INSERT INTO supervisor_feedback (intern_id_info, supervisor_name, note, rating)
        VALUES ({ph},{ph},{ph},{ph})
        """,
        (intern_id, supervisor_name, note, rating)
    )

    conn.commit()
    conn.close()

    return result
