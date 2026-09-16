/**
 * Application Layer Activity & Protocol Visualizer - Frontend Engine
 * Manages WebSocket synchronization, dual-panel state, interactive playback,
 * and dynamic packet inspection animations.
 */

(function () {
  "use strict";

  // --- Global State ---
  const state = {
    ws: null,
    isConnected: false,
    activeMode: "browsing", // "browsing" | "mail" | "streaming"
    currentActivity: null,
    currentStepIndex: 0,
    totalSteps: 0,
    isPlaying: false,
    currentStepData: null,
    allStepsSummary: [],
    reconnectInterval: 2000,
    mockBufferPercent: 0,
    mockChunksLoaded: 0,
  };

  // --- DOM Elements ---
  const elements = {
    // Header
    wsBadge: document.getElementById("ws-badge"),
    wsStatusText: document.getElementById("ws-status-text"),

    // Mode Tabs & Views
    tabBrowsing: document.getElementById("tab-browsing"),
    tabMail: document.getElementById("tab-mail"),
    tabStreaming: document.getElementById("tab-streaming"),
    viewBrowsing: document.getElementById("view-browsing"),
    viewMail: document.getElementById("view-mail"),
    viewStreaming: document.getElementById("view-streaming"),

    // Browsing Inputs
    urlInput: document.getElementById("url-input"),
    btnVisit: document.getElementById("btn-visit"),
    browsingStatus: document.getElementById("browsing-status"),
    browsingLog: document.getElementById("browsing-log-content"),

    // Mail Inputs
    mailTo: document.getElementById("mail-to"),
    mailSubject: document.getElementById("mail-subject"),
    mailBody: document.getElementById("mail-body"),
    btnSendMail: document.getElementById("btn-send-mail"),
    mailStatus: document.getElementById("mail-status"),
    mailLog: document.getElementById("mail-log-content"),

    // Streaming Inputs
    streamQuality: document.getElementById("stream-quality"),
    btnStreamPlay: document.getElementById("btn-stream-play"),
    btnStreamPause: document.getElementById("btn-stream-pause"),
    streamStatus: document.getElementById("stream-status"),
    streamLog: document.getElementById("stream-log-content"),
    playerScreen: document.getElementById("player-screen"),
    playerQualityBadge: document.getElementById("player-quality-badge"),
    playerStatusIcon: document.getElementById("player-status-icon"),
    bufferFill: document.getElementById("buffer-fill"),
    playerChunkLabel: document.getElementById("player-chunk-label"),

    // Playback Controls
    btnReplay: document.getElementById("btn-replay"),
    btnPrevStep: document.getElementById("btn-prev-step"),
    btnPauseResume: document.getElementById("btn-pause-resume"),
    labelPauseResume: document.getElementById("label-pause-resume"),
    btnNextStep: document.getElementById("btn-next-step"),

    // Meta bar
    currentActivityTag: document.getElementById("current-activity-tag"),
    stepCounter: document.getElementById("step-counter"),
    relativeTimeTag: document.getElementById("relative-time-tag"),

    // Stepper Nav
    stepperNav: document.getElementById("stepper-nav"),

    // Direction Banner
    clientEndpoint: document.getElementById("client-endpoint"),
    serverTitle: document.getElementById("server-title"),
    serverEndpoint: document.getElementById("server-endpoint"),
    arrowHead: document.getElementById("arrow-head"),
    packetProtocolBadge: document.getElementById("packet-protocol-badge"),
    packetSummaryLabel: document.getElementById("packet-summary-label"),

    // Details
    highlightsGrid: document.getElementById("highlights-grid"),
    wireCode: document.getElementById("wire-code"),
    btnCopyWire: document.getElementById("btn-copy-wire"),
    explanationText: document.getElementById("explanation-text"),
  };

  // --- WebSocket Connection Management ---
  function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
      state.isConnected = true;
      elements.wsBadge.className = "connection-badge connected";
      elements.wsStatusText.textContent = "Live WS Connected";
      logActivity(state.activeMode, "system", "Connected to visualizer WebSocket server.");
    };

    state.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleServerMessage(msg);
      } catch (err) {
        console.error("Error parsing WebSocket message:", err);
      }
    };

    state.ws.onclose = () => {
      state.isConnected = false;
      elements.wsBadge.className = "connection-badge disconnected";
      elements.wsStatusText.textContent = "Disconnected (Reconnecting...)";
      setTimeout(initWebSocket, state.reconnectInterval);
    };

    state.ws.onerror = (err) => {
      console.warn("WebSocket encountered error:", err);
    };
  }

  function sendWS(action, data = {}) {
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
      alert("WebSocket connection is not open yet. Please wait a moment.");
      return;
    }
    const payload = { action, ...data };
    state.ws.send(JSON.stringify(payload));
  }

  // --- Server Message Dispatcher ---
  function handleServerMessage(msg) {
    switch (msg.event) {
      case "session_initialized":
        onSessionInitialized(msg);
        break;
      case "step_update":
        onStepUpdate(msg);
        break;
      case "playback_state":
        onPlaybackState(msg);
        break;
      case "error":
        console.error("Server Error:", msg.error_message);
        logActivity(state.activeMode, "system", `Error: ${msg.error_message}`);
        break;
      default:
        break;
    }
  }

  function onSessionInitialized(msg) {
    state.currentActivity = msg.activity_type;
    state.currentStepIndex = msg.current_step_index;
    state.totalSteps = msg.total_steps;
    state.isPlaying = msg.is_playing;
    state.allStepsSummary = msg.all_steps_summary || [];

    // Reset mock streaming buffer when new session starts
    if (msg.activity_type === "streaming") {
      state.mockBufferPercent = 0;
      state.mockChunksLoaded = 0;
      updateStreamingMockPlayer(false);
    }

    updateControlsUI();
    renderStepperNav();
    updateActivityStatus(msg.activity_type, msg.status_text, "active");

    if (msg.log_message) {
      logActivity(msg.activity_type, "system", msg.log_message);
    }

    if (msg.step) {
      renderStepDetail(msg.step);
    }
  }

  function onStepUpdate(msg) {
    state.currentStepIndex = msg.current_step_index;
    state.totalSteps = msg.total_steps;
    state.isPlaying = msg.is_playing;

    updateControlsUI();
    updateStepperHighlight();

    if (msg.step) {
      state.currentStepData = msg.step;
      renderStepDetail(msg.step);

      // Log in appropriate panel
      const dirClass = msg.step.direction === "client_to_server" ? "client" : "server";
      logActivity(
        msg.activity_type || state.activeMode,
        dirClass,
        `[${msg.step.protocol}] ${msg.step.summary}`
      );
    }

    const isFinal = state.currentStepIndex === state.totalSteps;
    const badgeType = isFinal ? "success" : "active";
    updateActivityStatus(msg.activity_type, msg.status_text, badgeType);

    // Streaming player visual feedback
    if (msg.activity_type === "streaming" && msg.step) {
      handleStreamingStepSideEffects(msg.step);
    }
  }

  function onPlaybackState(msg) {
    state.isPlaying = msg.is_playing;
    state.currentStepIndex = msg.current_step_index;
    updateControlsUI();

    if (msg.log_message) {
      logActivity(state.currentActivity || state.activeMode, "system", msg.log_message);
    }
    if (msg.status_text) {
      updateActivityStatus(
        state.currentActivity,
        msg.status_text,
        state.isPlaying ? "active" : "paused"
      );
    }
  }

  function handleStreamingStepSideEffects(step) {
    if (step.summary.includes("Master Playlist")) {
      elements.playerStatusIcon.textContent = "📑 Master Manifest Loaded";
    } else if (step.summary.includes("Segment Schedule")) {
      elements.playerStatusIcon.textContent = "⏱ Chunk Schedule Received";
    } else if (step.summary.includes("segment_1042.ts") && step.direction === "server_to_client") {
      state.mockBufferPercent = 50;
      state.mockChunksLoaded = 1;
      updateStreamingMockPlayer(true);
    } else if (step.summary.includes("segment_1043.ts") && step.direction === "server_to_client") {
      state.mockBufferPercent = 100;
      state.mockChunksLoaded = 2;
      updateStreamingMockPlayer(true);
    }
  }

  function updateStreamingMockPlayer(isPlaying) {
    elements.bufferFill.style.width = `${state.mockBufferPercent}%`;
    elements.playerChunkLabel.textContent = `Buffer: ${state.mockChunksLoaded} chunk(s) cached`;
    if (isPlaying) {
      elements.playerStatusIcon.textContent = "▶ Streaming Video (H.264/AAC)";
      elements.playerQualityBadge.textContent = elements.streamQuality.value.toUpperCase();
    } else {
      elements.playerStatusIcon.textContent = "⏸ Paused / Buffering";
    }
  }

  // --- Rendering Protocol Step Details ---
  function renderStepDetail(step) {
    // 1. Meta Bar
    elements.currentActivityTag.textContent = (state.currentActivity || "Activity").toUpperCase();
    elements.stepCounter.textContent = `Step ${step.step_id} / ${step.total_steps}`;
    elements.relativeTimeTag.textContent = `+${step.relative_time_ms} ms`;

    // 2. Direction Banner & Endpoints
    const isClientToServer = step.direction === "client_to_server";
    elements.clientEndpoint.textContent = isClientToServer ? step.sender : step.receiver;
    elements.serverEndpoint.textContent = isClientToServer ? step.receiver : step.sender;

    // Server title specialization
    if (step.protocol === "DNS") {
      elements.serverTitle.textContent = "DNS RESOLVER";
    } else if (step.protocol === "SMTP") {
      elements.serverTitle.textContent = "MAIL SERVER (MTA)";
    } else {
      elements.serverTitle.textContent = "WEB/CDN SERVER";
    }

    // Direction arrow head
    if (isClientToServer) {
      elements.arrowHead.className = "arrow-head arrow-head-right";
    } else {
      elements.arrowHead.className = "arrow-head arrow-head-left";
    }

    // Protocol badge style
    elements.packetProtocolBadge.textContent = step.protocol;
    elements.packetProtocolBadge.className = `packet-protocol-badge proto-${step.protocol.toLowerCase()}`;
    elements.packetSummaryLabel.textContent = step.summary;

    // 3. Highlighted Fields Grid
    renderHighlights(step.highlighted_fields);

    // 4. Wire Message
    elements.wireCode.textContent = step.raw_message;

    // 5. Educational Explanation
    elements.explanationText.textContent = step.explanation;
  }

  function renderHighlights(fields) {
    elements.highlightsGrid.innerHTML = "";
    if (!fields || fields.length === 0) {
      elements.highlightsGrid.innerHTML = `<div class="empty-highlights">No highlighted fields for this step.</div>`;
      return;
    }

    fields.forEach((field) => {
      const card = document.createElement("div");
      card.className = "highlight-card";
      card.innerHTML = `
        <span class="highlight-name">${escapeHtml(field.name)}</span>
        <span class="highlight-value">${escapeHtml(field.value)}</span>
        <span class="highlight-desc">${escapeHtml(field.description)}</span>
      `;
      elements.highlightsGrid.appendChild(card);
    });
  }

  // --- Stepper Navigation ---
  function renderStepperNav() {
    elements.stepperNav.innerHTML = "";
    if (!state.allStepsSummary || state.allStepsSummary.length === 0) {
      elements.stepperNav.innerHTML = `<div class="stepper-placeholder">Perform an activity on the left to initialize protocol steps</div>`;
      return;
    }

    state.allStepsSummary.forEach((s) => {
      const pill = document.createElement("button");
      pill.type = "button";
      pill.className = "step-pill";
      pill.dataset.stepId = s.step_id;
      pill.title = `${s.summary}`;

      const icon = s.direction === "client_to_server" ? "→" : "←";
      pill.textContent = `#${s.step_id} ${s.protocol} ${icon}`;

      pill.addEventListener("click", () => {
        sendWS("seek", { target_step: s.step_id });
      });

      elements.stepperNav.appendChild(pill);
    });

    updateStepperHighlight();
  }

  function updateStepperHighlight() {
    const pills = elements.stepperNav.querySelectorAll(".step-pill");
    pills.forEach((pill) => {
      const stepNum = parseInt(pill.dataset.stepId, 10);
      pill.classList.remove("active", "completed");
      if (stepNum === state.currentStepIndex) {
        pill.classList.add("active");
        pill.scrollIntoView({ behavior: "smooth", inline: "nearest", block: "nearest" });
      } else if (stepNum < state.currentStepIndex) {
        pill.classList.add("completed");
      }
    });
  }

  // --- UI Controls State ---
  function updateControlsUI() {
    if (state.isPlaying) {
      elements.labelPauseResume.textContent = "⏸ Pause";
      elements.btnPauseResume.className = "btn-ctrl btn-ctrl-primary";
    } else {
      elements.labelPauseResume.textContent = "▶ Resume";
      elements.btnPauseResume.className = "btn-ctrl";
    }

    elements.btnPrevStep.disabled = state.currentStepIndex <= 1;
    elements.btnNextStep.disabled = state.currentStepIndex >= state.totalSteps;
  }

  function updateActivityStatus(activityType, text, type = "active") {
    if (!activityType) return;
    let badgeEl = null;
    if (activityType === "browsing") badgeEl = elements.browsingStatus;
    else if (activityType === "mail") badgeEl = elements.mailStatus;
    else if (activityType === "streaming") badgeEl = elements.streamStatus;

    if (badgeEl && text) {
      badgeEl.textContent = text;
      badgeEl.className = `status-value badge badge-${type}`;
    }
  }

  function logActivity(activityType, type, message) {
    let logContainer = null;
    if (activityType === "browsing") logContainer = elements.browsingLog;
    else if (activityType === "mail") logContainer = elements.mailLog;
    else if (activityType === "streaming") logContainer = elements.streamLog;

    if (!logContainer) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const entry = document.createElement("div");
    entry.className = `log-entry log-${type}`;
    entry.textContent = `[${timeStr}] ${message}`;

    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
  }

  // --- Mode Tab Switching ---
  function switchMode(newMode) {
    state.activeMode = newMode;

    [elements.tabBrowsing, elements.tabMail, elements.tabStreaming].forEach((tab) => {
      tab.classList.remove("active");
    });
    [elements.viewBrowsing, elements.viewMail, elements.viewStreaming].forEach((view) => {
      view.classList.remove("active");
    });

    if (newMode === "browsing") {
      elements.tabBrowsing.classList.add("active");
      elements.viewBrowsing.classList.add("active");
    } else if (newMode === "mail") {
      elements.tabMail.classList.add("active");
      elements.viewMail.classList.add("active");
    } else if (newMode === "streaming") {
      elements.tabStreaming.classList.add("active");
      elements.viewStreaming.classList.add("active");
    }
  }

  // --- Event Listeners Setup ---
  function setupEventListeners() {
    // Mode Switchers
    elements.tabBrowsing.addEventListener("click", () => switchMode("browsing"));
    elements.tabMail.addEventListener("click", () => switchMode("mail"));
    elements.tabStreaming.addEventListener("click", () => switchMode("streaming"));

    // Quick URL Presets
    document.querySelectorAll(".btn-preset").forEach((btn) => {
      btn.addEventListener("click", () => {
        elements.urlInput.value = btn.dataset.url;
      });
    });

    // Clear Logs
    document.querySelectorAll(".btn-clear-log").forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetId = btn.dataset.target;
        const target = document.getElementById(targetId);
        if (target) target.innerHTML = "";
      });
    });

    // Activity 1: Browsing "Visit"
    elements.btnVisit.addEventListener("click", () => {
      const url = elements.urlInput.value.trim();
      if (!url) {
        alert("Please enter a valid URL.");
        return;
      }
      switchMode("browsing");
      logActivity("browsing", "client", `User clicked Visit: ${url}`);
      updateActivityStatus("browsing", "Connecting to DNS & Server...", "active");

      sendWS("start_activity", {
        activity_type: "browsing",
        params: { url },
      });
    });

    elements.urlInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        elements.btnVisit.click();
      }
    });

    // Activity 2: Mail "Send Mail"
    elements.btnSendMail.addEventListener("click", () => {
      const to = elements.mailTo.value.trim();
      const subject = elements.mailSubject.value.trim();
      const body = elements.mailBody.value.trim();

      if (!to || !subject) {
        alert("Please provide both recipient and subject.");
        return;
      }

      switchMode("mail");
      logActivity("mail", "client", `User clicked Send Mail to: ${to}`);
      updateActivityStatus("mail", "Initializing SMTP dialogue...", "active");

      sendWS("start_activity", {
        activity_type: "mail",
        params: {
          to,
          subject,
          body,
          from: "student@course.edu",
        },
      });
    });

    // Activity 3: Streaming Play & Pause
    elements.btnStreamPlay.addEventListener("click", () => {
      const quality = elements.streamQuality.value;
      switchMode("streaming");
      logActivity("streaming", "client", `Play stream requested at ${quality}`);
      updateActivityStatus("streaming", "Fetching master playlist...", "active");
      elements.playerQualityBadge.textContent = quality.toUpperCase();

      sendWS("start_activity", {
        activity_type: "streaming",
        params: { quality },
      });
    });

    elements.btnStreamPause.addEventListener("click", () => {
      logActivity("streaming", "client", "Stream pause requested.");
      updateStreamingMockPlayer(false);
      sendWS("pause");
    });

    // Playback Toolbar Controls
    elements.btnPauseResume.addEventListener("click", () => {
      if (state.isPlaying) {
        sendWS("pause");
      } else {
        sendWS("resume");
      }
    });

    elements.btnPrevStep.addEventListener("click", () => {
      sendWS("prev_step");
    });

    elements.btnNextStep.addEventListener("click", () => {
      sendWS("next_step");
    });

    elements.btnReplay.addEventListener("click", () => {
      sendWS("replay");
    });

    // Copy Wire Payload
    elements.btnCopyWire.addEventListener("click", () => {
      const text = elements.wireCode.textContent;
      navigator.clipboard.writeText(text).then(() => {
        const original = elements.btnCopyWire.textContent;
        elements.btnCopyWire.textContent = "Copied!";
        setTimeout(() => {
          elements.btnCopyWire.textContent = original;
        }, 1500);
      });
    });
  }

  // --- Utility Functions ---
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // --- Bootstrap ---
  window.addEventListener("DOMContentLoaded", () => {
    setupEventListeners();
    initWebSocket();
  });
})();
