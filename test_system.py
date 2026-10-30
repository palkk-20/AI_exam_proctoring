import numpy as np
import cv2
import base64
from fastapi.testclient import TestClient
from app.main import app
from app.proctor_engine import analyze_frame, save_violation_snapshot

client = TestClient(app)

def test_routes():
    print("[1] Testing web routes...")
    r = client.get("/")
    assert r.status_code == 200, f"Landing failed: {r.status_code}"
    print("  [OK] Landing page OK")

    r = client.get("/system-check")
    assert r.status_code == 200, f"System check failed: {r.status_code}"
    print("  [OK] System check page OK")

    r = client.get("/admin")
    assert r.status_code == 200, f"Admin page failed: {r.status_code}"
    print("  [OK] Admin dashboard OK")

    r = client.get("/api/admin/stats")
    assert r.status_code == 200, f"Stats failed: {r.status_code}"
    print("  [OK] Admin stats API OK:", r.json())

def test_exam_flow():
    print("\n[2] Testing Exam Flow...")
    # Start exam
    r = client.post("/api/exam/start", json={
        "name": "Aman Verma",
        "roll_no": "TEST-2026-99",
        "email": "aman@example.com"
    })
    assert r.status_code == 200
    data = r.json()
    session_id = data["session_id"]
    print(f"  [OK] Exam started with session: {session_id}")

    # Fetch questions
    r = client.get(f"/api/exam/{session_id}/questions")
    assert r.status_code == 200
    questions = r.json()["questions"]
    assert len(questions) == 5
    print(f"  [OK] Fetched {len(questions)} questions")

    # Generate synthetic dummy frame
    blank_img = np.zeros((240, 320, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', blank_img)
    img_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode()

    # Report violation
    r = client.post("/api/proctor/violation", json={
        "session_id": session_id,
        "violation_type": "TAB_SWITCH",
        "description": "Candidate switched tabs to search engine",
        "severity": "HIGH",
        "snapshot_base64": img_b64
    })
    assert r.status_code == 200
    res_viol = r.json()
    print("  [OK] Violation reported, current integrity:", res_viol["current_integrity"])
    assert res_viol["current_integrity"] < 100

    # Submit exam
    r = client.post("/api/exam/submit", json={
        "session_id": session_id,
        "answers": {str(questions[0]["id"]): 1, str(questions[1]["id"]): 2}
    })
    assert r.status_code == 200
    print("  [OK] Exam submitted successfully:", r.json())

    # Get result
    r = client.get(f"/api/exam/{session_id}/result")
    assert r.status_code == 200
    print("  [OK] Exam audit result retrieved. Infractions:", len(r.json()["violations"]))

def test_cv_engine():
    print("\n[3] Testing OpenCV Proctor Engine...")
    # Test blank image (should detect NO_FACE)
    blank = np.zeros((200, 200, 3), dtype=np.uint8)
    res = analyze_frame(blank)
    print("  [OK] CV Analysis on blank frame:", res["status"], "-", res["reason"])
    assert res["status"] in ["LOW_LIGHT", "NO_FACE"]

if __name__ == "__main__":
    print("=" * 50)
    print(" RUNNING SENTINEL AI PROCTOR INTEGRATION TESTS")
    print("=" * 50)
    test_routes()
    test_exam_flow()
    test_cv_engine()
    print("=" * 50)
    print(" ALL TESTS PASSED SUCCESSFULLY! ")
    print("=" * 50)
