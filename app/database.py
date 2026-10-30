import sqlite3
import json
from contextlib import contextmanager
from app.config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()

    # Candidates table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        roll_no TEXT UNIQUE NOT NULL,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Exam Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exam_sessions (
        id TEXT PRIMARY KEY,
        candidate_id INTEGER,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        status TEXT DEFAULT 'IN_PROGRESS', -- 'IN_PROGRESS', 'COMPLETED', 'TERMINATED'
        initial_integrity INTEGER DEFAULT 100,
        current_integrity INTEGER DEFAULT 100,
        score INTEGER DEFAULT 0,
        total_questions INTEGER DEFAULT 5,
        violation_count INTEGER DEFAULT 0,
        FOREIGN KEY (candidate_id) REFERENCES candidates(id)
    );
    """)

    # Violations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS violations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        violation_type TEXT NOT NULL,
        description TEXT NOT NULL,
        severity TEXT DEFAULT 'MEDIUM', -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
        penalty INTEGER DEFAULT 0,
        snapshot_filename TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES exam_sessions(id)
    );
    """)

    # Questions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL,
        options TEXT NOT NULL, -- JSON list of strings
        correct_index INTEGER NOT NULL,
        category TEXT DEFAULT 'Computer Science'
    );
    """)

    # Submissions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE NOT NULL,
        answers TEXT NOT NULL, -- JSON dict of question_id: selected_index
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES exam_sessions(id)
    );
    """)

    # Insert sample questions if table is empty
    cursor.execute("SELECT COUNT(*) FROM questions")
    if cursor.fetchone()[0] == 0:
        sample_questions = [
            (
                "Which data structure operates on a Last-In, First-Out (LIFO) basis?",
                json.dumps(["Queue", "Stack", "Binary Tree", "Linked List"]),
                1,
                "Data Structures"
            ),
            (
                "What is the average time complexity of searching in a Hash Map?",
                json.dumps(["O(n)", "O(log n)", "O(1)", "O(n^2)"]),
                2,
                "Algorithms"
            ),
            (
                "In Python, which keyword is used to handle exceptions gracefully?",
                json.dumps(["try...except", "do...catch", "catch...throw", "error...handle"]),
                0,
                "Python"
            ),
            (
                "Which HTTP method is typically idempotent and used to retrieve resources?",
                json.dumps(["POST", "PATCH", "GET", "CONNECT"]),
                2,
                "Web & Networking"
            ),
            (
                "What is the primary function of an AI Face Detection model in automated proctoring?",
                json.dumps([
                    "To generate randomized exam questions",
                    "To verify student presence and identify suspicious head movement/multiple people",
                    "To grade subjective essays automatically",
                    "To accelerate internet network speed"
                ]),
                1,
                "AI & Proctoring"
            )
        ]
        cursor.executemany(
            "INSERT INTO questions (question_text, options, correct_index, category) VALUES (?, ?, ?, ?)",
            sample_questions
        )

    conn.commit()
    conn.close()
