from datetime import datetime
from db import connect
from rag import retrieve

def generate_ai_clone(intern_id_info: str, supervisor_note: str):
    conn = connect()
    cur = conn.cursor()

    intern = cur.execute("SELECT * FROM interns WHERE id_info=?", (intern_id_info,)).fetchone()
    if not intern:
        conn.close()
        return {"error": "Intern not found"}

    # last feedback
    last_fb = cur.execute(
        "SELECT supervisor_name, note, rating, created_at FROM supervisor_feedback WHERE intern_id_info=? ORDER BY feedback_id DESC LIMIT 1",
        (intern_id_info,)
    ).fetchone()

    conn.close()

    memories = retrieve(intern_id_info, top_k=8)
    note = (supervisor_note or "").lower()

    score = 70
    strengths, weaknesses, actions, tags = [], [], [], []

    # Signals from intern learning_skill
    ls = (intern.get("learning_skill") or "").lower()
    if "django" in ls or "backend" in ls:
        strengths.append("Backend track (Django) is on progress")
        tags += ["django", "backend"]; score += 3
    if "react" in ls or "frontend" in ls:
        strengths.append("Frontend track (React) is on progress")
        tags += ["react", "frontend"]; score += 3
    if "cyber" in ls or "security" in ls:
        strengths.append("Cybersecurity learning is active")
        tags += ["cybersecurity"]; score += 3
    if "flutter" in ls:
        strengths.append("Flutter learning is active")
        tags += ["flutter"]; score += 2
    if "qa" in ls:
        strengths.append("QA/testing learning is active")
        tags += ["qa", "testing"]; score += 2
    if "seo" in ls:
        strengths.append("SEO learning is active")
        tags += ["seo"]; score += 1

    # Signal from rating (if present)
    pr = intern.get("progress_rating_num")
    if pr is not None:
        if pr >= 4:
            score += 8
        elif pr <= 1:
            score -= 8

    # Supervisor note rules
    if "doc" in note or "documentation" in note:
        weaknesses.append("Documentation needs improvement")
        actions.append("Write README + API/docs for completed work")
        tags.append("documentation"); score -= 6

    if "delay" in note or "late" in note or "slow" in note:
        weaknesses.append("Time estimation / pacing needs improvement")
        actions.append("Daily time-boxing + report blockers early")
        tags.append("planning"); score -= 8

    if "good" in note or "great" in note or "excellent" in note:
        strengths.append("Positive supervisor note recorded")
        score += 4

    if not strengths:
        strengths = ["Active participation in internship program"]
    if not weaknesses:
        weaknesses = ["Needs clearer weekly goals and measurable outputs"]
        actions.append("Set weekly goals and send weekly progress summary")

    score = max(0, min(100, score))
    risk_flag = score < 60 or ("delay" in note) or ("late" in note)
    risk_reason = "Possible deadline/consistency risk" if risk_flag else "No major risk observed"

    return {
        "intern_id": intern_id_info,
        "intern_name": intern.get("name"),
        "learning_skill": intern.get("learning_skill"),
        "project": intern.get("working_on_project"),
        "progress_score": score,
        "strengths": list(dict.fromkeys(strengths))[:6],
        "weaknesses": list(dict.fromkeys(weaknesses))[:6],
        "action_plan": list(dict.fromkeys(actions))[:8],
        "skill_tags": list(dict.fromkeys(tags))[:12],
        "supervisor_note": supervisor_note,
        "risk_flag": bool(risk_flag),
        "risk_reason": risk_reason,
        "rag_used": memories,
        "last_feedback": dict(last_fb) if last_fb else None,
        "generated_at": datetime.utcnow().isoformat()
    }
