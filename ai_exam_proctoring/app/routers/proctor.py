from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
import json
import sqlite3
from typing import List, Dict, Any
from app.database import get_db
from app.models import ViolationReportRequest
from app.config import PENALTIES
from app.proctor_engine import decode_base64_image, analyze_frame, save_violation_snapshot

router = APIRouter(prefix="/api/proctor", tags=["proctor"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.session_subscribers: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_to_proctors(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dc in dead_connections:
            if dc in self.active_connections:
                self.active_connections.remove(dc)

ws_manager = ConnectionManager()

@router.websocket("/ws")
async def proctor_websocket(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Can receive ping or admin commands
            try:
                msg = json.loads(data)
                if msg.get("type") == "PING":
                    await websocket.send_json({"type": "PONG"})
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

@router.post("/violation")
async def report_violation(req: ViolationReportRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM exam_sessions WHERE id = ?", (req.session_id,))
    session = cursor.fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] != "IN_PROGRESS":
        return {"status": "ignored", "message": "Exam not active"}

    penalty = PENALTIES.get(req.violation_type.upper(), 5)
    current_integrity = max(0, session["current_integrity"] - penalty)
    violation_count = session["violation_count"] + 1

    # Save evidence snapshot if available
    snapshot_filename = None
    if req.snapshot_base64:
        try:
            image = decode_base64_image(req.snapshot_base64)
            if image is not None:
                snapshot_filename = save_violation_snapshot(image, req.session_id, req.violation_type)
        except Exception as e:
            print("Failed to save snapshot:", e)

    # Insert violation record
    cursor.execute(
        """
        INSERT INTO violations (session_id, violation_type, description, severity, penalty, snapshot_filename)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (req.session_id, req.violation_type, req.description, req.severity, penalty, snapshot_filename)
    )

    # Update session integrity
    cursor.execute(
        """
        UPDATE exam_sessions
        SET current_integrity = ?, violation_count = ?
        WHERE id = ?
        """,
        (current_integrity, violation_count, req.session_id)
    )
    db.commit()

    # Get candidate info for websocket broadcast
    cursor.execute("SELECT name, roll_no FROM candidates WHERE id = ?", (session["candidate_id"],))
    cand = cursor.fetchone()

    # Broadcast event to admin/proctor dashboard
    await ws_manager.broadcast_to_proctors({
        "type": "NEW_VIOLATION",
        "session_id": req.session_id,
        "candidate_name": cand["name"] if cand else "Unknown",
        "roll_no": cand["roll_no"] if cand else "N/A",
        "violation_type": req.violation_type,
        "description": req.description,
        "severity": req.severity,
        "penalty": penalty,
        "current_integrity": current_integrity,
        "snapshot_url": f"/snapshots/{snapshot_filename}" if snapshot_filename else None,
        "timestamp": cursor.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]
    })

    return {
        "status": "recorded",
        "current_integrity": current_integrity,
        "penalty": penalty,
        "snapshot_filename": snapshot_filename
    }

@router.post("/analyze-frame")
def analyze_webcam_frame(payload: dict):
    """Direct server-side analysis of a base64 frame with OpenCV"""
    frame_b64 = payload.get("frame_base64", "")
    if not frame_b64:
        raise HTTPException(status_code=400, detail="frame_base64 required")

    image = decode_base64_image(frame_b64)
    result = analyze_frame(image)
    return result
