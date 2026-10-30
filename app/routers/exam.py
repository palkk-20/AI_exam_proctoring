from fastapi import APIRouter, HTTPException, Depends
import uuid
import json
import sqlite3
from datetime import datetime
from app.database import get_db
from app.models import CandidateRegisterRequest, ExamSubmitRequest
from app.config import TOTAL_QUESTIONS

router = APIRouter(prefix="/api/exam", tags=["exam"])

@router.post("/start")
def start_exam(req: CandidateRegisterRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    
    # Insert or update candidate
    cursor.execute("SELECT id FROM candidates WHERE roll_no = ?", (req.roll_no,))
    existing = cursor.fetchone()
    if existing:
        candidate_id = existing["id"]
        cursor.execute("UPDATE candidates SET name = ?, email = ? WHERE id = ?", (req.name, req.email, candidate_id))
    else:
        cursor.execute(
            "INSERT INTO candidates (name, roll_no, email) VALUES (?, ?, ?)",
            (req.name, req.roll_no, req.email)
        )
        candidate_id = cursor.lastrowid

    # Create new session
    session_id = str(uuid.uuid4())
    cursor.execute(
        """
        INSERT INTO exam_sessions (id, candidate_id, start_time, status, initial_integrity, current_integrity, total_questions)
        VALUES (?, ?, CURRENT_TIMESTAMP, 'IN_PROGRESS', 100, 100, ?)
        """,
        (session_id, candidate_id, TOTAL_QUESTIONS)
    )
    db.commit()

    return {
        "status": "success",
        "session_id": session_id,
        "candidate": {
            "name": req.name,
            "roll_no": req.roll_no
        }
    }

@router.get("/{session_id}/questions")
def get_questions(session_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT status FROM exam_sessions WHERE id = ?", (session_id,))
    session = cursor.fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail="Exam is not active")

    cursor.execute("SELECT id, question_text, options, category FROM questions LIMIT ?", (TOTAL_QUESTIONS,))
    rows = cursor.fetchall()
    
    questions = []
    for r in rows:
        questions.append({
            "id": r["id"],
            "question_text": r["question_text"],
            "options": json.loads(r["options"]),
            "category": r["category"]
        })
    return {"questions": questions}

@router.post("/submit")
def submit_exam(req: ExamSubmitRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM exam_sessions WHERE id = ?", (req.session_id,))
    session = cursor.fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] == "COMPLETED":
        return {"status": "already_submitted", "message": "Exam has already been submitted"}

    # Fetch correct answers
    cursor.execute("SELECT id, correct_index FROM questions")
    correct_map = {str(r["id"]): r["correct_index"] for r in cursor.fetchall()}

    # Calculate score
    score = 0
    total = len(correct_map)
    for q_id, selected_idx in req.answers.items():
        if q_id in correct_map and correct_map[q_id] == selected_idx:
            score += 1

    # Save submission
    cursor.execute(
        """
        INSERT OR REPLACE INTO submissions (session_id, answers, submitted_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        """,
        (req.session_id, json.dumps(req.answers))
    )

    # Update session status
    cursor.execute(
        """
        UPDATE exam_sessions 
        SET status = 'COMPLETED', end_time = CURRENT_TIMESTAMP, score = ?, total_questions = ?
        WHERE id = ?
        """,
        (score, total, req.session_id)
    )
    db.commit()

    return {
        "status": "success",
        "score": score,
        "total": total,
        "percentage": round((score / total) * 100, 1) if total > 0 else 0,
        "integrity": session["current_integrity"]
    }

@router.get("/{session_id}/result")
def get_exam_result(session_id: str, db: sqlite3.Connection = Depends(get_db)):
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
