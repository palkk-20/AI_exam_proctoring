/**
 * Real-time Proctor / Administrator Command Dashboard
 * Supports: Live Monitoring, Dynamic Question Bank Management (Add/Delete/Search),
 * Multi-camera surveillance, and Session Interventions.
 */

document.addEventListener("DOMContentLoaded", () => {
  let ws = null;
  let currentInspectingSessionId = null;

  // DOM Elements - Stats
  const totalCandEl = document.getElementById("stat-total-candidates");
  const activeExamsEl = document.getElementById("stat-active-exams");
  const totalViolationsEl = document.getElementById("stat-total-violations");
  const flaggedSessionsEl = document.getElementById("stat-flagged-sessions");
  const sessionsTableBody = document.getElementById("sessions-table-body");
  const liveTicker = document.getElementById("live-ticker");

  // DOM Elements - Audit Modal
  const modal = document.getElementById("audit-modal");
  const modalClose = document.getElementById("modal-close-btn");
  const modalCandidateName = document.getElementById("modal-candidate-name");
  const modalRollNo = document.getElementById("modal-roll-no");
  const modalIntegrityBadge = document.getElementById("modal-integrity-badge");
  const modalStatusBadge = document.getElementById("modal-status-badge");
  const modalScoreText = document.getElementById("modal-score-text");
  const modalSnapshotGallery = document.getElementById("modal-snapshot-gallery");
  const modalViolationsTable = document.getElementById("modal-violations-table");
  const btnSendWarning = document.getElementById("btn-send-warning");
  const btnTerminateSession = document.getElementById("btn-terminate-session");

  // Initialize
  initWebSocket();
  fetchStats();
  fetchSessions();

  // Polling fallback
  setInterval(() => {
    fetchStats();
    fetchSessions();
  }, 7000);

  // ==========================================
  // 1. WEBSOCKET REAL-TIME FEED
  // ==========================================
  function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/proctor/ws`;
    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => console.log("Connected to Proctor WebSocket Feed.");

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleLiveEvent(data);
        } catch (e) {
          console.error("WS error:", e);
        }
      };

      ws.onclose = () => {
        console.warn("WS closed, attempting reconnection in 3s...");
        setTimeout(initWebSocket, 3000);
      };
    } catch (err) {
      console.warn("WebSocket init failed:", err);
    }
  }

  function handleLiveEvent(data) {
    if (data.type === "NEW_VIOLATION") {
      addTickerAlert(data);
      fetchStats();
      fetchSessions();

      if (currentInspectingSessionId === data.session_id) {
        openSessionAudit(data.session_id);
      }
    }
  }

  function addTickerAlert(v) {
    if (!liveTicker) return;
    const item = document.createElement("div");
    item.className = "incident-item";
    item.style.backgroundColor = "rgba(239, 68, 68, 0.1)";
    item.style.border = "1px solid rgba(239, 68, 68, 0.3)";
    item.style.borderRadius = "8px";
    item.style.padding = "0.6rem 0.85rem";
    item.style.marginBottom = "0.5rem";

    item.innerHTML = `
      <span class="badge-clean badge-red" style="margin-right:0.4rem;">${v.violation_type}</span>
      <strong style="color:#0f172a;">${v.candidate_name} (${v.roll_no}):</strong> 
      <span style="color:#334155;">${v.description}</span>
      <span style="color:#64748b; font-size:0.75rem; margin-left:auto; font-family:monospace;">${v.timestamp || "Just now"}</span>
    `;

    liveTicker.prepend(item);

    while (liveTicker.children.length > 15) {
      liveTicker.removeChild(liveTicker.lastChild);
    }
  }

  // ==========================================
  // 2. STATS & SESSIONS LIST
  // ==========================================
  async function fetchStats() {
    try {
      const res = await fetch("/api/admin/stats");
      const data = await res.json();
      if (totalCandEl) totalCandEl.textContent = data.total_candidates;
      if (activeExamsEl) activeExamsEl.textContent = data.active_sessions;
      if (totalViolationsEl) totalViolationsEl.textContent = data.total_violations;
      if (flaggedSessionsEl) flaggedSessionsEl.textContent = data.flagged_sessions;
    } catch (err) {
      console.warn("Stats fetch failed:", err);
    }
  }

  async function fetchSessions() {
    try {
      const res = await fetch("/api/admin/sessions");
      const data = await res.json();
      renderSessions(data.sessions || []);
    } catch (err) {
      console.warn("Sessions fetch failed:", err);
    }
  }

  function renderSessions(sessions) {
    if (!sessionsTableBody) return;
    sessionsTableBody.innerHTML = "";

    if (sessions.length === 0) {
      sessionsTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#64748b; padding: 2rem;">No active exam sittings recorded yet. Start an exam from the Candidate Portal to see live surveillance.</td></tr>`;
      return;
    }

    sessions.forEach((s) => {
      const tr = document.createElement("tr");

      let integrityBadgeClass = "badge-green";
      if (s.current_integrity < 60) integrityBadgeClass = "badge-red";
      else if (s.current_integrity < 80) integrityBadgeClass = "badge-amber";

      let statusBadgeClass = "badge-blue";
      if (s.status === "COMPLETED") statusBadgeClass = "badge-green";
      if (s.status === "TERMINATED") statusBadgeClass = "badge-red";

      tr.innerHTML = `
        <td><strong>${s.candidate_name}</strong></td>
        <td><code>${s.roll_no}</code></td>
        <td><span class="badge-clean ${statusBadgeClass}">${s.status}</span></td>
        <td>
          <div style="display:flex; align-items:center; gap:0.5rem;">
            <span class="badge-clean ${integrityBadgeClass}">${s.current_integrity}%</span>
            <div style="width:50px; height:6px; background:#e2e8f0; border-radius:3px; overflow:hidden;">
              <div style="width:${s.current_integrity}%; height:100%; background:${s.current_integrity < 60 ? '#ef4444' : s.current_integrity < 80 ? '#f59e0b' : '#10b981'};"></div>
            </div>
          </div>
        </td>
        <td><strong>${s.violation_count}</strong></td>
        <td>${s.score !== null ? `${s.score} / ${s.total_questions}` : "In Progress"}</td>
        <td>
          <button class="btn inspect-btn" style="padding:0.4rem 0.85rem; font-size:0.8rem; background:#2563eb; color:#fff;" data-id="${s.id}">
            🔍 Audit Session
          </button>
        </td>
      `;

      tr.querySelector(".inspect-btn").addEventListener("click", () => {
        openSessionAudit(s.id);
      });

      sessionsTableBody.appendChild(tr);
    });
  }

  // ==========================================
  // 3. AUDIT MODAL & INTERVENTIONS
  // ==========================================
  async function openSessionAudit(sessionId) {
    currentInspectingSessionId = sessionId;
    try {
      const res = await fetch(`/api/admin/session/${sessionId}`);
      const data = await res.json();
      const s = data.session;
      const violations = data.violations;

      modalCandidateName.textContent = s.candidate_name;
      modalRollNo.textContent = `Student ID: ${s.roll_no} | Session UID: ${s.id.substring(0, 8)}...`;
      modalIntegrityBadge.textContent = `Integrity: ${s.current_integrity}%`;
      modalIntegrityBadge.className = `badge-clean ${s.current_integrity < 60 ? 'badge-red' : s.current_integrity < 80 ? 'badge-amber' : 'badge-green'}`;
      modalStatusBadge.textContent = s.status;
      modalScoreText.textContent = s.score !== null ? `${s.score} / ${s.total_questions}` : "In Progress";

      modalViolationsTable.innerHTML = "";
      if (violations.length === 0) {
        modalViolationsTable.innerHTML = `<tr><td colspan="4" style="text-align:center; color:#64748b; padding:1.25rem;">Clean session! No malpractice detected.</td></tr>`;
      } else {
        violations.forEach(v => {
          const row = document.createElement("tr");
          row.innerHTML = `
            <td><code>${v.timestamp}</code></td>
            <td><span class="badge-clean badge-red">${v.violation_type}</span></td>
            <td>${v.description}</td>
            <td style="color:#ef4444; font-weight:bold;">-${v.penalty}%</td>
          `;
          modalViolationsTable.appendChild(row);
        });
      }

      modalSnapshotGallery.innerHTML = "";
      const snapshots = violations.filter(v => v.snapshot_filename);
      if (snapshots.length === 0) {
        modalSnapshotGallery.innerHTML = `<p style="color:#64748b; font-size:0.85rem; padding:1rem;">No photographic infractions logged for this candidate.</p>`;
      } else {
        snapshots.forEach(sn => {
          const card = document.createElement("div");
          card.className = "evidence-card";
          card.innerHTML = `
            <a href="/snapshots/${sn.snapshot_filename}" target="_blank">
              <img src="/snapshots/${sn.snapshot_filename}" alt="Evidence" loading="lazy" />
            </a>
            <div class="evidence-meta">
              <div style="font-weight:700; color:#ef4444;">${sn.violation_type}</div>
              <div style="color:#64748b; font-size:0.75rem;">${sn.timestamp}</div>
            </div>
          `;
          modalSnapshotGallery.appendChild(card);
        });
      }

      modal.style.display = "flex";
    } catch (e) {
      console.error(e);
      alert("Failed to load session details");
    }
  }

  if (modalClose) {
    modalClose.addEventListener("click", () => {
      modal.style.display = "none";
      currentInspectingSessionId = null;
    });
  }

  if (btnSendWarning) {
    btnSendWarning.addEventListener("click", async () => {
      if (!currentInspectingSessionId) return;
      const msg = prompt("Enter warning message to send to candidate:", "Proctor Alert: Please focus directly on your screen and avoid suspicious movement.");
      if (msg) {
        await fetch(`/api/admin/session/${currentInspectingSessionId}/action`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "WARNING", message: msg })
        });
        alert("Warning sent to candidate screen!");
      }
    });
  }

  if (btnTerminateSession) {
    btnTerminateSession.addEventListener("click", async () => {
      if (!currentInspectingSessionId) return;
      if (confirm("Are you sure you want to forcibly terminate this exam session? The candidate will be disqualified.")) {
        await fetch(`/api/admin/session/${currentInspectingSessionId}/action`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "TERMINATE", message: "Disqualified by proctor." })
        });
        alert("Exam session disqualified!");
        openSessionAudit(currentInspectingSessionId);
        fetchSessions();
      }
    });
  }
});

