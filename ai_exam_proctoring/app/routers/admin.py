from fastapi import APIRouter, HTTPException, Depends
import sqlite3
import json
from app.database import get_db
from app.models import AdminActionRequest, QuestionCreateRequest
from app.routers.proctor import ws_manager

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/stats")
def get_dashboard_stats(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM candidates")
    total_candidates = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM exam_sessions WHERE status = 'IN_PROGRESS'")
    active_sessions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM violations")
    total_violations = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM exam_sessions WHERE current_integrity < 60")
    flagged_sessions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM questions")
    total_questions = cursor.fetchone()[0]

    return {
        "total_candidates": total_candidates,
        "active_sessions": active_sessions,
        "total_violations": total_violations,
        "flagged_sessions": flagged_sessions,
        "total_questions": total_questions
    }

@router.get("/sessions")
def list_sessions(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT s.*, c.name as candidate_name, c.roll_no, c.email
        FROM exam_sessions s
        JOIN candidates c ON s.candidate_id = c.id
        ORDER BY s.start_time DESC
        """
    )
    rows = cursor.fetchall()
    return {"sessions": [dict(r) for r in rows]}

@router.get("/session/{session_id}")
def get_session_details(session_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT s.*, c.name as candidate_name, c.roll_no, c.email
        FROM exam_sessions s
        JOIN candidates c ON s.candidate_id = c.id
        WHERE s.id = ?
        """,
        (session_id,)
    )
    session = cursor.fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    cursor.execute("SELECT * FROM violations WHERE session_id = ? ORDER BY timestamp DESC", (session_id,))
    violations = [dict(v) for v in cursor.fetchall()]

    return {
        "session": dict(session),
        "violations": violations
    }

@router.post("/session/{session_id}/action")
async def take_admin_action(session_id: str, req: AdminActionRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM exam_sessions WHERE id = ?", (session_id,))
    session = cursor.fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if req.action == "TERMINATE":
        cursor.execute("UPDATE exam_sessions SET status = 'TERMINATED' WHERE id = ?", (session_id,))
        db.commit()
        await ws_manager.broadcast_to_proctors({
            "type": "SESSION_TERMINATED",
            "session_id": session_id,
            "message": req.message or "Session terminated by proctor for severe malpractice."
        })
        return {"status": "terminated"}

    elif req.action == "WARNING":
        await ws_manager.broadcast_to_proctors({
            "type": "PROCTOR_WARNING",
            "session_id": session_id,
            "message": req.message or "Official warning from Proctor: Cease suspicious activity immediately!"
        })
        return {"status": "warning_sent"}

    return {"status": "unknown_action"}

# ==========================================
# QUESTION BANK CRUD APIS
# ==========================================

@router.get("/questions")
def get_all_questions(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, question_text, options, correct_index, category FROM questions ORDER BY id DESC")
    rows = cursor.fetchall()
    questions = []
    for r in rows:
        questions.append({
            "id": r["id"],
            "question_text": r["question_text"],
            "options": json.loads(r["options"]),
            "correct_index": r["correct_index"],
            "category": r["category"]
        })
    return {"questions": questions, "count": len(questions)}

@router.post("/questions")
def add_new_question(req: QuestionCreateRequest, db: sqlite3.Connection = Depends(get_db)):
    if not req.question_text.strip():
        raise HTTPException(status_code=400, detail="Question text cannot be empty")
    if len(req.options) < 2:
        raise HTTPException(status_code=400, detail="At least 2 options are required")
    
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO questions (question_text, options, correct_index, category)
        VALUES (?, ?, ?, ?)
        """,
        (req.question_text.strip(), json.dumps(req.options), req.correct_index, req.category or "General")
    )
    db.commit()
    new_id = cursor.lastrowid
    return {
        "status": "success",
        "message": "Question added successfully",
        "question_id": new_id
    }

@router.delete("/questions/{question_id}")
def delete_question(question_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    db.commit()
    return {"status": "deleted", "question_id": question_id}

@router.get("/violations")
def list_all_violations(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT v.*, c.name as candidate_name, c.roll_no
        FROM violations v
        JOIN exam_sessions s ON v.session_id = s.id
        JOIN candidates c ON s.candidate_id = c.id
        ORDER BY v.timestamp DESC LIMIT 50
        """
    )
    rows = cursor.fetchall()
    return {"violations": [dict(r) for r in rows]}

@router.get("/candidates")
def list_all_candidates(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM candidates ORDER BY created_at DESC")
    rows = cursor.fetchall()
    return {"candidates": [dict(r) for r in rows]}
