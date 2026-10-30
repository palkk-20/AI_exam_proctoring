# 🛡️ SentinelAI - AI Online Exam Proctoring System

An enterprise-ready, intelligent automated exam proctoring system powered by **Computer Vision, Audio Forensics, and Browser Sandbox Security**.

---

## 🌟 Key Features (मुख्य विशेषताएँ)

### 1. 👁️ Real-time Computer Vision & Face Tracking
- **Multi-Face Detection**: Identifies when a secondary person enters the candidate's camera frame and triggers a critical warning.
- **Absence / No Face Detected**: Alerts if the candidate leaves the camera frame or ducks down.
- **Gaze & Head Pose Estimation**: Tracks if the student looks away from the screen (e.g. towards notes, secondary devices, or looking sideways).
- **Illumination & Lighting Checks**: Alerts if the room lighting is insufficient or faces are shadowed.

### 2. 🎙️ Acoustic Speech & Audio Analysis
- **Web Audio API Analyzer**: Measures ambient noise levels and decibels in real time.
- **Conversation & Whispering Detection**: Flags continuous speaking, external whispers, or sudden sound spikes.

### 3. 🔒 Browser Sandbox & Integrity Lockdown
- **Tab Switch Detection**: Detects `visibilitychange` and window `blur` events (switching tabs, opening Google, or Alt+Tab).
- **Fullscreen Enforcement**: Forces candidate into full-screen mode; warns and logs an infraction if exited.
- **Shortcut & Clipboard Lockdown**: Blocks `Ctrl+C`, `Ctrl+V`, `F12`, `Ctrl+Shift+I` (DevTools), and right-click context menu.

### 4. 📸 Automated Photo Evidence & Incident Logging
- Captures timestamped webcam snapshot proof whenever an infraction occurs.
- Annotates snapshots with red violation bounding box and timestamp watermark.
- Automatically calculates and deducts integrity points from the candidate's **100% Integrity Index**.

### 5. 📊 Live Invigilator / Proctor Command Center
- Real-time **WebSocket feed** showing instant violation alerts across all active candidate sessions.
- Candidate surviellance table with live integrity score gauges.
- Deep Audit Inspector: Review photographic evidence snapshots, send custom warning messages, or force-terminate sessions.

---

## 🏗️ Project Architecture (प्रोजेक्ट संरचना)

```text
ai_exam_proctoring/
├── app/
│   ├── config.py              # Configuration, penalty weights & thresholds
│   ├── database.py            # SQLite schema, tables, and question seed
│   ├── models.py              # Pydantic schemas for API requests
│   ├── proctor_engine.py      # OpenCV computer vision frame analyzer & snapshot annotation
│   ├── routers/
│   │   ├── exam.py            # Exam flow, question serving & score calculation
│   │   ├── proctor.py         # Violation logging, snapshot capture & WebSocket broadcast
│   │   └── admin.py           # Surveillance dashboard stats, audit & interventions
│   ├── static/
│   │   ├── css/styles.css     # Modern glassmorphism UI & Proctor HUD theme
│   │   ├── js/proctor_ai.js   # Client-side AI vision, audio & watchdog engine
│   │   ├── js/exam.js         # Exam question navigator & timer controller
│   │   └── js/dashboard.js    # Live proctor dashboard & WebSocket consumer
│   ├── templates/
│   │   ├── index.html         # Landing page (Candidate vs Invigilator)
│   │   ├── system_check.html  # Hardware & camera/mic calibration pre-check
│   │   ├── exam.html          # Secure candidate exam room with Proctor HUD
│   │   ├── result.html        # Comprehensive exam score & integrity audit report
│   │   └── admin.html         # Live surveillance command center
├── data/
│   ├── models/                # Haar cascade face & eye detection models
│   ├── snapshots/             # Saved visual evidence snapshots
│   └── proctor.db             # SQLite database
├── requirements.txt           # Python dependencies
├── run.py                     # One-click startup script
└── README.md                  # Documentation
```

---

## 🚀 How to Run the Project (प्रोजेक्ट कैसे चलाएं)

### 1. Requirements
- Python 3.10+ (tested on Python 3.14)
- Modern web browser (Chrome, Edge, Brave, or Firefox)
- Working webcam and microphone

### 2. Install Dependencies (if not already installed)
```bash
pip install -r requirements.txt
```

### 3. Launch the Application
```bash
python run.py
```
Or with uvicorn directly:
```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Access URLs
- 🎓 **Candidate Exam Portal**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- 📊 **Proctor Command Center**: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)
- 📑 **API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🧪 Testing the AI Proctoring System (सिस्टम को टेस्ट कैसे करें)

1. Open [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin) in one browser tab or window (Proctor view).
2. Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in another window or in an incognito window:
   - Click **"Begin System Check & Exam"**.
   - Fill in candidate details (Name, Roll Number).
   - Test camera & mic calibration, then click **"Launch Exam"**.
3. In the Exam Room, try these test actions:
   - **Look away from camera**: Move your head sideways or look down &rarr; Watch the system trigger a *Looking Away* warning and audible beep.
   - **Cover the camera or duck**: &rarr; Watch it trigger *No Face Detected*.
   - **Have a second person appear**: &rarr; Watch it trigger *Multiple Faces Detected*.
   - **Switch to another tab or Alt+Tab**: &rarr; Watch it trigger *Tab Switch Detected*.
   - **Press Escape to exit fullscreen**: &rarr; Watch the Fullscreen warning modal appear.
   - **Speak loudly into microphone**: &rarr; Watch the mic sensitivity bar hit red and trigger *Audio Spike*.
4. Now check the **Proctor Command Center** tab:
   - See the real-time live alert ticker flash with the new incident.
   - Click **"Audit Session"** to view timestamped photo evidence snapshots and candidate metrics.
5. Finish and submit the exam &rarr; Inspect the comprehensive **Integrity Audit Report & Certificate**.
