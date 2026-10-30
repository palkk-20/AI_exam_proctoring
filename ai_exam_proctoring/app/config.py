import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
MODELS_DIR = DATA_DIR / "models"
DB_PATH = DATA_DIR / "proctor.db"

SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Penalty deductions from initial 100% integrity
PENALTIES = {
    "MULTIPLE_FACES": 15,
    "NO_FACE": 10,
    "LOOKING_AWAY": 5,
    "TAB_SWITCH": 12,
    "FULLSCREEN_EXIT": 10,
    "AUDIO_SPIKE": 6,
    "KEYBOARD_SHORTCUT": 5,
    "SUSPICIOUS_OBJECT": 20
}

# Integrity Thresholds
CRITICAL_THRESHOLD = 50   # Auto-flag for manual review or disqualification
WARNING_THRESHOLD = 75    # Display prominent warnings to candidate

# Exam Configuration
EXAM_DURATION_MINUTES = 10
TOTAL_QUESTIONS = 5
