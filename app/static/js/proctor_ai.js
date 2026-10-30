/**
 * AI Online Exam Proctoring Engine
 * Real-time vision, audio, and environmental integrity monitoring.
 */

class AIProctorEngine {
  constructor(options = {}) {
    this.sessionId = options.sessionId || null;
    this.videoElement = options.videoElement || document.getElementById('webcam-video');
    this.canvasElement = options.canvasElement || document.getElementById('overlay-canvas');
    this.integrityFill = options.integrityFill || document.getElementById('integrity-fill');
    this.integrityScoreText = options.integrityScoreText || document.getElementById('integrity-score');
    this.incidentList = options.incidentList || document.getElementById('incident-list');
    
    this.audioMeterFill = document.getElementById('audio-bar-fill');
    this.stream = null;
    this.audioContext = null;
    this.analyser = null;
    this.audioData = null;

    this.currentIntegrity = 100;
    this.isRunning = false;
    this.cooldowns = {};
    this.faceDetector = null;

    // Check native FaceDetector API support
    if (window.FaceDetector) {
      try {
        this.faceDetector = new window.FaceDetector({ fastMode: true, maxDetectedFaces: 5 });
      } catch (e) {
        console.warn("Native FaceDetector failed, falling back to backend CV:", e);
      }
    }
  }

  async start() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 } },
        audio: true
      });

      if (this.videoElement) {
        this.videoElement.srcObject = this.stream;
        await this.videoElement.play();
      }

      this.initAudioMonitoring();
      this.initEnvironmentWatchdogs();
      this.isRunning = true;

      // Start vision analysis loop
      this.runVisionLoop();
      console.log("AI Proctoring Engine Initialized Successfully.");
    } catch (err) {
      console.error("Camera/Mic access error:", err);
      this.showToast("Camera & Microphone access is required to take the exam!", "danger");
    }
  }

  initAudioMonitoring() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioCtx();
      const source = this.audioContext.createMediaStreamSource(this.stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 512;
      this.analyser.smoothingTimeConstant = 0.4;
      source.connect(this.analyser);
      this.audioData = new Uint8Array(this.analyser.frequencyBinCount);

      this.audioLoop();
    } catch (e) {
      console.warn("Audio monitoring init failed:", e);
    }
  }

  audioLoop() {
    if (!this.isRunning) return;

    this.analyser.getByteFrequencyData(this.audioData);
    let sum = 0;
    for (let i = 0; i < this.audioData.length; i++) {
      sum += this.audioData[i];
    }
    const avg = sum / this.audioData.length;
    const volumePercent = Math.min(100, Math.round((avg / 128) * 100));

    if (this.audioMeterFill) {
      this.audioMeterFill.style.width = `${volumePercent}%`;
      if (volumePercent > 65) {
        this.audioMeterFill.style.backgroundColor = '#ef4444';
      } else {
        this.audioMeterFill.style.backgroundColor = '#06b6d4';
      }
    }

    // Trigger violation if excessive noise/talking detected
    if (volumePercent > 68) {
      this.reportViolation("AUDIO_SPIKE", "High audio level / talking detected", "LOW");
    }

    requestAnimationFrame(() => this.audioLoop());
  }

  initEnvironmentWatchdogs() {
    // 1. Tab Switch / Window Blur
    document.addEventListener("visibilitychange", () => {
      if (document.hidden && this.isRunning) {
        this.reportViolation("TAB_SWITCH", "Candidate switched browser tab or minimized window", "HIGH");
      }
    });

    window.addEventListener("blur", () => {
      if (this.isRunning) {
        this.reportViolation("TAB_SWITCH", "Candidate clicked outside exam window", "MEDIUM");
      }
    });

    // 2. Fullscreen Exit
    document.addEventListener("fullscreenchange", () => {
      if (!document.fullscreenElement && this.isRunning) {
        this.reportViolation("FULLSCREEN_EXIT", "Candidate exited fullscreen exam mode", "HIGH");
        const modal = document.getElementById("fullscreen-modal");
        if (modal) modal.style.display = "flex";
      }
    });

    // 3. Disable Copy, Paste, Cut & Context Menu
    document.addEventListener("contextmenu", (e) => e.preventDefault());
    document.addEventListener("copy", (e) => {
      e.preventDefault();
      this.reportViolation("KEYBOARD_SHORTCUT", "Attempted text copy detected", "LOW");
    });
    document.addEventListener("paste", (e) => {
      e.preventDefault();
      this.reportViolation("KEYBOARD_SHORTCUT", "Attempted text paste detected", "LOW");
    });

    // 4. Disable DevTools & Alt/Ctrl Keys
    document.addEventListener("keydown", (e) => {
      if (
        e.key === "F12" ||
        (e.ctrlKey && e.shiftKey && (e.key === "I" || e.key === "J" || e.key === "C")) ||
        (e.ctrlKey && (e.key === "u" || e.key === "U"))
      ) {
        e.preventDefault();
        this.reportViolation("KEYBOARD_SHORTCUT", "Attempted developer tools / source code inspection", "HIGH");
      }
    });
  }

  async runVisionLoop() {
    if (!this.isRunning) return;

    try {
      await this.analyzeVisionFrame();
    } catch (err) {
      console.warn("Vision cycle error:", err);
    }

    // Run cycle every 1.6 seconds
    setTimeout(() => this.runVisionLoop(), 1600);
  }

  async analyzeVisionFrame() {
    if (!this.videoElement || this.videoElement.videoWidth === 0) return;

    const canvas = this.canvasElement;
    if (!canvas) return;

    canvas.width = this.videoElement.videoWidth;
    canvas.height = this.videoElement.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Method A: Native FaceDetector (ultra fast in Chrome/Edge)
    if (this.faceDetector) {
      try {
        const faces = await this.faceDetector.detect(this.videoElement);
        this.renderFaceHUD(ctx, faces);

        if (faces.length === 0) {
          this.reportViolation("NO_FACE", "No face detected in webcam frame", "HIGH");
        } else if (faces.length > 1) {
          this.reportViolation("MULTIPLE_FACES", `Multiple faces detected (${faces.length} people)`, "CRITICAL");
        } else {
          // Check head pose / position (single face)
          const f = faces[0].boundingBox;
          const centerX = f.x + f.width / 2;
          const frameCenterX = canvas.width / 2;
          const offsetRatio = Math.abs(centerX - frameCenterX) / canvas.width;

          if (offsetRatio > 0.32) {
            this.reportViolation("LOOKING_AWAY", "Candidate looking away or head turned aside", "MEDIUM");
          }
        }
        return;
      } catch (e) {
        // Fall back to server analysis
      }
    }

    // Method B: Send frame to backend OpenCV
    await this.callBackendVisionAnalysis();
  }

  async callBackendVisionAnalysis() {
    const frameB64 = this.captureSnapshotBase64();
    if (!frameB64) return;

    try {
      const res = await fetch("/api/proctor/analyze-frame", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ frame_base64: frameB64 })
      });
      const data = await res.json();

      if (data.status === "NO_FACE") {
        this.reportViolation("NO_FACE", data.reason, "HIGH");
      } else if (data.status === "MULTIPLE_FACES") {
        this.reportViolation("MULTIPLE_FACES", data.reason, "CRITICAL");
      } else if (data.status === "SUSPICIOUS_POSE") {
        this.reportViolation("LOOKING_AWAY", data.reason, "MEDIUM");
      }

      // Render boxes from backend if canvas present
      if (this.canvasElement && data.face_boxes) {
        const ctx = this.canvasElement.getContext("2d");
        ctx.clearRect(0, 0, this.canvasElement.width, this.canvasElement.height);
        ctx.strokeStyle = data.face_count === 1 ? "#06b6d4" : "#ef4444";
        ctx.lineWidth = 3;
        for (const box of data.face_boxes) {
          ctx.strokeRect(box.x, box.y, box.w, box.h);
        }
      }
    } catch (e) {
      console.warn("Backend vision error:", e);
    }
  }

  renderFaceHUD(ctx, faces) {
    for (const f of faces) {
      const b = f.boundingBox;
      ctx.strokeStyle = faces.length === 1 ? "#06b6d4" : "#ef4444";
      ctx.lineWidth = 3;
      ctx.strokeRect(b.x, b.y, b.width, b.height);

      // Draw corner brackets for high-tech HUD look
      const cornerLen = 15;
      ctx.strokeStyle = "#38bdf8";
      ctx.beginPath();
      // Top-Left
      ctx.moveTo(b.x, b.y + cornerLen); ctx.lineTo(b.x, b.y); ctx.lineTo(b.x + cornerLen, b.y);
      // Top-Right
      ctx.moveTo(b.x + b.width - cornerLen, b.y); ctx.lineTo(b.x + b.width, b.y); ctx.lineTo(b.x + b.width, b.y + cornerLen);
      ctx.stroke();

      // Landmarks if available
      if (f.landmarks) {
        ctx.fillStyle = "#38bdf8";
        for (const lm of f.landmarks) {
          ctx.beginPath();
          ctx.arc(lm.location.x, lm.location.y, 3, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }
  }

  captureSnapshotBase64() {
    if (!this.videoElement || this.videoElement.videoWidth === 0) return null;
    const offscreen = document.createElement("canvas");
    offscreen.width = 480;
    offscreen.height = 360;
    const ctx = offscreen.getContext("2d");
    ctx.drawImage(this.videoElement, 0, 0, offscreen.width, offscreen.height);
    return offscreen.toDataURL("image/jpeg", 0.7);
  }

  async reportViolation(type, description, severity = "MEDIUM") {
    const now = Date.now();
    // Cooldown: minimum 4 seconds between same violation type
    if (this.cooldowns[type] && now - this.cooldowns[type] < 4000) {
      return;
    }
    this.cooldowns[type] = now;

    // Visual HUD warning
    const camBox = document.getElementById("camera-container");
    if (camBox) {
      camBox.classList.add("violation");
      setTimeout(() => camBox.classList.remove("violation"), 2000);
    }

    // Play audible alert sound
    this.playWarningTone();
    this.showToast(`⚠️ Warning: ${description}`, "danger");

    // Add to incident list
    this.addIncidentUI(type, description);

    // Capture evidence snapshot
    const snapshotB64 = this.captureSnapshotBase64();

    // Send to backend
    if (this.sessionId) {
      try {
        const res = await fetch("/api/proctor/violation", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: this.sessionId,
            violation_type: type,
            description: description,
            severity: severity,
            snapshot_base64: snapshotB64
          })
        });
        const data = await res.json();
        if (data.current_integrity !== undefined) {
          this.updateIntegrityUI(data.current_integrity);
        }
      } catch (err) {
        console.error("Failed to report violation:", err);
      }
    }
  }

  playWarningTone() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const ctx = this.audioContext || new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(600, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(300, ctx.currentTime + 0.25);
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.01, ctx.currentTime + 0.25);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.25);
    } catch (e) {
      // Audio autoplay restrictions
    }
  }

  updateIntegrityUI(score) {
    this.currentIntegrity = score;
    if (this.integrityScoreText) {
      this.integrityScoreText.textContent = `${score}%`;
    }
    if (this.integrityFill) {
      this.integrityFill.style.width = `${score}%`;
      if (score < 50) {
        this.integrityFill.style.backgroundColor = "#ef4444";
      } else if (score < 75) {
        this.integrityFill.style.backgroundColor = "#f59e0b";
      } else {
        this.integrityFill.style.backgroundColor = "#10b981";
      }
    }
  }

  addIncidentUI(type, desc) {
    if (!this.incidentList) return;
    const timeStr = new Date().toLocaleTimeString();
    const item = document.createElement("div");
    item.className = "incident-item";
    item.innerHTML = `
      <span class="badge badge-danger">${type}</span>
      <span style="flex:1;">${desc}</span>
      <span style="color:#64748b; font-size:0.75rem;">${timeStr}</span>
    `;
    this.incidentList.prepend(item);
  }

  showToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.className = "toast-container";
      document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = `toast`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 4500);
  }

  stop() {
    this.isRunning = false;
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
    }
    if (this.audioContext && this.audioContext.state !== "closed") {
      this.audioContext.close();
    }
  }
}

window.AIProctorEngine = AIProctorEngine;
