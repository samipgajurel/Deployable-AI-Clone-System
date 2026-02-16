from db import connect, is_postgres

def generate_clone(intern_id, supervisor_name, note, rating):
    conn = connect()
    cur = conn.cursor()

    if is_postgres():
        ph = "%s"
    else:
        ph = "?"

    # ---- Get intern ----
    cur.execute(f"SELECT * FROM interns WHERE id_info={ph}", (intern_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return {"error": "Intern not found"}

    (
        id_info,
        name,
        email,
        learning_skill,
        working_on_project,
        progress_month1,
        knowledge_gained,
        progress_rating_num
    ) = row

    # ---- Get RAG memory ----
    cur.execute(
        f"SELECT text FROM rag_records WHERE intern_id_info={ph}",
        (intern_id,)
    )
    rag_rows = cur.fetchall()
    rag_texts = [r[0] for r in rag_rows] if rag_rows else []

    # ---- AI Logic (simple evaluation model) ----
    strengths = []
    weaknesses = []

    if rating >= 4:
        strengths.append("Strong performance")
    else:
        weaknesses.append("Needs improvement")

    if knowledge_gained:
        strengths.append("Learning actively")

    if "documentation" in note.lower():
        weaknesses.append("Documentation lacking")

    action_plan = [
        "Weekly progress reporting",
        "Improve code documentation",
        "Supervisor review every Friday"
    ]

    result = {
        "intern": name,
        "project": working_on_project,
        "progress_score": rating,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "action_plan": action_plan,
        "memory_used": rag_texts
    }

    # ---- Store supervisor feedback ----
    cur.execute(f"""
        INSERT INTO supervisor_feedback
        (intern_id_info, supervisor_name, note, rating)
        VALUES ({ph},{ph},{ph},{ph})
    """, (intern_id, supervisor_name, note, rating))

    conn.commit()
    conn.close()

    return result
