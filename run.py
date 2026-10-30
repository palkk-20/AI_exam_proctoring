import uvicorn
import sys
import webbrowser
import threading
import time

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    print("=" * 65)
    print(" 🛡️  SENTINEL AI ONLINE EXAM PROCTORING SYSTEM STARTING...")
    print("=" * 65)
    print(" 👉 Candidate Portal:       http://127.0.0.1:8000")
    print(" 👉 Proctor Command Center: http://127.0.0.1:8000/admin")
    print(" 👉 API Documentation:      http://127.0.0.1:8000/docs")
    print("=" * 65)
    print(" Press Ctrl+C to stop the server.")
    print("=" * 65)

    # Launch browser automatically
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
