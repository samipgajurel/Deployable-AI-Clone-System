from rag import retrieve
from db import connect

def generate_ai(intern_id, note):

    conn = connect()
    cur = conn.cursor()
    intern = cur.execute("SELECT * FROM interns WHERE id_info=?",(intern_id,)).fetchone()
    conn.close()

    memories = retrieve(intern_id)

    score = 70

    if intern["rating"] >= 4:
        score += 10
    if "delay" in note.lower():
        score -= 10

    return {
        "intern": intern["name"],
        "learning_skill": intern["learning_skill"],
        "project": intern["project"],
        "progress_score": score,
        "supervisor_note": note,
        "memory_used": memories
    }
