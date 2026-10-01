/**
 * Application & Transport Layer Activity & Protocol Visualizer - Frontend Engine
 * Manages WebSocket synchronization, dual-panel layout, layer switching (L4/L7),
 * interactive playback, cross-layer bidirectional linking, and dynamic packet animations.
 */

(function () {
  "use strict";

  // --- Global State ---
  const state = {
    ws: null,
    isConnected: false,
    activeMode: "browsing", // "browsing" | "mail" | "streaming"
    activeLayer: "application", // "application" | "transport"
    currentActivity: null,
    currentStepIndex: 0,
    totalSteps: 0,
    isPlaying: false,
    currentStepData: null,
    allStepsSummary: [],
    transportSegments: [],
    currentTransportSegment: null,
    currentTransportIndex: 0,
    transportStats: null,
    simulateLoss: false,
    reconnectInterval: 2000,
    mockBufferPercent: 0,
    mockChunksLoaded: 0,
  };

  // --- DOM Elements ---
  const elements = {
    // Header
    wsBadge: document.getElementById("ws-badge"),
    wsStatusText: document.getElementById("ws-status-text"),

    // Left Panel: Mode Tabs & Views
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

    // Layer Switcher Tabs
    tabLayerApp: document.getElementById("tab-layer-app"),
    tabLayerTransport: document.getElementById("tab-layer-transport"),
    viewLayerApp: document.getElementById("view-layer-app"),
    viewLayerTransport: document.getElementById("view-layer-transport"),

    // Shared Meta & Controls
    btnReplay: document.getElementById("btn-replay"),
    btnPrevStep: document.getElementById("btn-prev-step"),
    btnPauseResume: document.getElementById("btn-pause-resume"),
    labelPauseResume: document.getElementById("label-pause-resume"),
    btnNextStep: document.getElementById("btn-next-step"),
    currentActivityTag: document.getElementById("current-activity-tag"),
    stepCounter: document.getElementById("step-counter"),
    relativeTimeTag: document.getElementById("relative-time-tag"),

    // Application Layer View Elements
    stepperNav: document.getElementById("stepper-nav"),
    appCrossLayerBanner: document.getElementById("app-cross-layer-banner"),
    appLinkedTransportLabel: document.getElementById("app-linked-transport-label"),
    btnJumpToTransport: document.getElementById("btn-jump-to-transport"),
    clientEndpoint: document.getElementById("client-endpoint"),
    serverTitle: document.getElementById("server-title"),
    serverEndpoint: document.getElementById("server-endpoint"),
    arrowHead: document.getElementById("arrow-head"),
    packetProtocolBadge: document.getElementById("packet-protocol-badge"),
    packetSummaryLabel: document.getElementById("packet-summary-label"),
    highlightsGrid: document.getElementById("highlights-grid"),
    wireCode: document.getElementById("wire-code"),
    btnCopyWire: document.getElementById("btn-copy-wire"),
    explanationText: document.getElementById("explanation-text"),

    // Transport Layer View Elements
    tcpClientState: document.getElementById("tcp-client-state"),
    tcpServerState: document.getElementById("tcp-server-state"),
    tcpWindowMetric: document.getElementById("tcp-window-metric"),
    tcpCwndMetric: document.getElementById("tcp-cwnd-metric"),
    transportStepperNav: document.getElementById("transport-stepper-nav"),
    transportLinkedAppLabel: document.getElementById("transport-linked-app-label"),
    btnJumpToApp: document.getElementById("btn-jump-to-app"),
    tcpSrcEndpoint: document.getElementById("tcp-src-endpoint"),
    tcpDstEndpoint: document.getElementById("tcp-dst-endpoint"),
    tcpFlagsBadges: document.getElementById("tcp-flags-badges"),
    transportArrowHead: document.getElementById("transport-arrow-head"),
    transportSummaryLabel: document.getElementById("transport-summary-label"),
    tcpFieldSeq: document.getElementById("tcp-field-seq"),
    tcpFieldAck: document.getElementById("tcp-field-ack"),
    tcpFieldWin: document.getElementById("tcp-field-win"),
    tcpFieldLen: document.getElementById("tcp-field-len"),
    tcpFieldFlags: document.getElementById("tcp-field-flags"),
    tcpFieldStates: document.getElementById("tcp-field-states"),
    transportWireCode: document.getElementById("transport-wire-code"),
    btnCopyTransportWire: document.getElementById("btn-copy-transport-wire"),
    transportExplanationText: document.getElementById("transport-explanation-text"),

    // Statistics
    statTotalPackets: document.getElementById("stat-total-packets"),
    statTcpSegments: document.getElementById("stat-tcp-segments"),
    statAppMessages: document.getElementById("stat-app-messages"),
    statBytesTransferred: document.getElementById("stat-bytes-transferred"),
    statRetransmissions: document.getElementById("stat-retransmissions"),
    statConnectionState: document.getElementById("stat-connection-state"),

    // Network Fault Control
    checkboxSimulateLoss: document.getElementById("checkbox-simulate-loss"),
    lossToggleLabel: document.getElementById("loss-toggle-label"),
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
      console.warn("WebSocket not ready yet; message dropped:", action);
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
    state.transportSegments = msg.transport_segments || [];
    state.transportStats = msg.transport_stats || null;

    if (msg.activity_type === "streaming") {
      state.mockBufferPercent = 0;
      state.mockChunksLoaded = 0;
      updateStreamingMockPlayer(false);
    }

    updateControlsUI();
    renderAppStepperNav();
    renderTransportStepperNav();
    updateActivityStatus(msg.activity_type, msg.status_text, "active");

    if (msg.log_message) {
      logActivity(msg.activity_type, "system", msg.log_message);
    }

    if (msg.step) {
      state.currentStepData = msg.step;
      renderAppStepDetail(msg.step);
    }

    if (msg.current_transport_segment) {
      state.currentTransportSegment = msg.current_transport_segment;
      state.currentTransportIndex = msg.current_transport_segment.id;
      renderTransportDetail(msg.current_transport_segment);
    } else if (state.transportSegments.length > 0) {
      state.currentTransportSegment = state.transportSegments[0];
      state.currentTransportIndex = 1;
      renderTransportDetail(state.transportSegments[0]);
    }

    if (state.transportStats) {
      renderTransportStats(state.transportStats);
    }
  }

  function onStepUpdate(msg) {
    state.currentStepIndex = msg.current_step_index;
    state.totalSteps = msg.total_steps;
    state.isPlaying = msg.is_playing;

    if (msg.transport_segments) {
      state.transportSegments = msg.transport_segments;
      renderTransportStepperNav();
    }

    updateControlsUI();
    updateAppStepperHighlight();

    if (msg.step) {
      state.currentStepData = msg.step;
      renderAppStepDetail(msg.step);

      const dirClass = msg.step.direction === "client_to_server" ? "client" : "server";
      logActivity(
        msg.activity_type || state.activeMode,
        dirClass,
        `[${msg.step.protocol}] ${msg.step.summary}`
      );
    }

    if (msg.current_transport_segment) {
      state.currentTransportSegment = msg.current_transport_segment;
      state.currentTransportIndex = msg.current_transport_segment.id;
      renderTransportDetail(msg.current_transport_segment);
      updateTransportStepperHighlight();
    }

    if (msg.transport_stats) {
      state.transportStats = msg.transport_stats;
      renderTransportStats(msg.transport_stats);
    }

    const isFinal = state.currentStepIndex === state.totalSteps;
    const badgeType = isFinal ? "success" : "active";
    updateActivityStatus(msg.activity_type, msg.status_text, badgeType);

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

  // --- Rendering Application Layer Step Details ---
  function renderAppStepDetail(step) {
    // 1. Meta Bar
    elements.currentActivityTag.textContent = (state.currentActivity || "Activity").toUpperCase();
    elements.stepCounter.textContent = `Step ${step.step_id} / ${step.total_steps}`;
    elements.relativeTimeTag.textContent = `+${step.relative_time_ms} ms`;

    // 2. Cross-layer Linkage
    if (step.transport_segment_ids && step.transport_segment_ids.length > 0) {
      const segIdStr = step.transport_segment_ids.map((id) => `#${id}`).join(", ");
      elements.appLinkedTransportLabel.textContent = `Carried via TCP Segments: ${segIdStr}`;
      elements.btnJumpToTransport.style.display = "inline-block";
    } else {
      elements.appLinkedTransportLabel.textContent = "No specific TCP segments linked";
      elements.btnJumpToTransport.style.display = "none";
    }

    // 3. Direction Banner & Endpoints
    const isClientToServer = step.direction === "client_to_server";
    elements.clientEndpoint.textContent = isClientToServer ? step.sender : step.receiver;
    elements.serverEndpoint.textContent = isClientToServer ? step.receiver : step.sender;

    if (step.protocol === "DNS") {
      elements.serverTitle.textContent = "DNS RESOLVER";
    } else if (step.protocol === "SMTP") {
      elements.serverTitle.textContent = "MAIL SERVER (MTA)";
    } else {
      elements.serverTitle.textContent = "WEB/CDN SERVER";
    }

    elements.arrowHead.className = isClientToServer
      ? "arrow-head arrow-head-right"
      : "arrow-head arrow-head-left";

    elements.packetProtocolBadge.textContent = step.protocol;
    elements.packetProtocolBadge.className = `packet-protocol-badge proto-${step.protocol.toLowerCase()}`;
    elements.packetSummaryLabel.textContent = step.summary;

    // 4. Highlighted Fields Grid
    renderHighlights(step.highlighted_fields);

    // 5. Wire Message & Explanation
    elements.wireCode.textContent = step.raw_message;
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

  // --- Rendering Transport Layer Segment Details ---
  function renderTransportDetail(segment) {
    if (!segment) return;

    // 1. TCP State Pill in state bar
    elements.tcpClientState.textContent = segment.client_state;
    elements.tcpServerState.textContent = segment.server_state;
    elements.tcpWindowMetric.textContent = `${segment.window.toLocaleString()} B`;

    // 2. Cross-layer Linkage back to Application Step
    if (segment.application_event_id) {
      elements.transportLinkedAppLabel.textContent = `Step #${segment.application_event_id} (Click to inspect application message)`;
      elements.btnJumpToApp.style.display = "inline-block";
    } else {
      elements.transportLinkedAppLabel.textContent = "None (TCP Transport Handshake / Control Segment)";
      elements.btnJumpToApp.style.display = "none";
    }

    // 3. Direction Banner
    const isClientToServer = segment.direction === "client_to_server";
    elements.tcpSrcEndpoint.textContent = `${segment.source_ip}:${segment.source_port}`;
    elements.tcpDstEndpoint.textContent = `${segment.destination_ip}:${segment.destination_port}`;

    elements.transportArrowHead.className = isClientToServer
      ? "arrow-head arrow-head-right"
      : "arrow-head arrow-head-left";

    // Flags Badges
    elements.tcpFlagsBadges.innerHTML = "";
    if (segment.protocol === "UDP") {
      const b = document.createElement("span");
      b.className = "tcp-flag-badge badge-syn";
      b.textContent = "UDP";
      elements.tcpFlagsBadges.appendChild(b);
    } else if (segment.flags && segment.flags.length > 0) {
      segment.flags.forEach((f) => {
        const b = document.createElement("span");
        b.className = `tcp-flag-badge badge-${f.toLowerCase()}`;
        b.textContent = f;
        elements.tcpFlagsBadges.appendChild(b);
      });
    } else {
      const b = document.createElement("span");
      b.className = "tcp-flag-badge badge-ack";
      b.textContent = "DATA";
      elements.tcpFlagsBadges.appendChild(b);
    }

    elements.transportSummaryLabel.textContent = segment.summary;

    // 4. TCP Key Fields Breakdown
    elements.tcpFieldSeq.textContent = segment.protocol === "UDP" ? "N/A (UDP)" : segment.seq.toLocaleString();
    elements.tcpFieldAck.textContent = segment.protocol === "UDP" ? "N/A (UDP)" : segment.ack.toLocaleString();
    elements.tcpFieldWin.textContent = segment.protocol === "UDP" ? "N/A" : `${segment.window.toLocaleString()} B`;
    elements.tcpFieldLen.textContent = `${segment.payload_length.toLocaleString()} bytes`;
    elements.tcpFieldFlags.textContent = segment.flags.length > 0 ? segment.flags.join(", ") : (segment.protocol === "UDP" ? "UDP" : "None");
    elements.tcpFieldStates.textContent = `Client: ${segment.client_state} | Server: ${segment.server_state}`;

    // 5. Wire Header Dissection & Explanation
    elements.transportWireCode.textContent = segment.raw_segment;
    elements.transportExplanationText.textContent = segment.explanation;
  }

  function renderTransportStats(stats) {
    if (!stats) return;
    elements.statTotalPackets.textContent = stats.total_packets;
    elements.statTcpSegments.textContent = stats.tcp_segments;
    elements.statAppMessages.textContent = stats.application_messages;
    elements.statBytesTransferred.textContent = `${stats.total_bytes.toLocaleString()} B`;
    elements.statRetransmissions.textContent = stats.retransmissions;
    elements.statConnectionState.textContent = stats.client_state;
    elements.tcpCwndMetric.textContent = `${stats.cwnd} MSS`;
  }

  // --- Stepper Navigation ---
  function renderAppStepperNav() {
    elements.stepperNav.innerHTML = "";
    if (!state.allStepsSummary || state.allStepsSummary.length === 0) {
      elements.stepperNav.innerHTML = `<div class="stepper-placeholder">Perform an activity on the left to initialize application steps</div>`;
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

    updateAppStepperHighlight();
  }

  function updateAppStepperHighlight() {
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

  function renderTransportStepperNav() {
    elements.transportStepperNav.innerHTML = "";
    if (!state.transportSegments || state.transportSegments.length === 0) {
      elements.transportStepperNav.innerHTML = `<div class="stepper-placeholder">Perform an activity to generate TCP/UDP segments</div>`;
      return;
    }

    state.transportSegments.forEach((seg) => {
      const pill = document.createElement("button");
      pill.type = "button";
      pill.className = "step-pill";
      pill.dataset.segId = seg.id;
      pill.title = seg.summary;

      const flagText = seg.flags.length > 0 ? seg.flags.join("+") : seg.protocol;
      const icon = seg.direction === "client_to_server" ? "→" : "←";
      pill.textContent = `#${seg.id} [${flagText}] ${icon}`;

      pill.addEventListener("click", () => {
        state.currentTransportSegment = seg;
        state.currentTransportIndex = seg.id;
        renderTransportDetail(seg);
        updateTransportStepperHighlight();

        // If this segment has a linked application event, highlight it in the background
        if (seg.application_event_id && seg.application_event_id !== state.currentStepIndex) {
          sendWS("seek", { target_step: seg.application_event_id });
        }
      });

      elements.transportStepperNav.appendChild(pill);
    });

    updateTransportStepperHighlight();
  }

  function updateTransportStepperHighlight() {
    const pills = elements.transportStepperNav.querySelectorAll(".step-pill");
    pills.forEach((pill) => {
      const segId = parseInt(pill.dataset.segId, 10);
      pill.classList.remove("active", "completed");
      if (segId === state.currentTransportIndex) {
        pill.classList.add("active");
        pill.scrollIntoView({ behavior: "smooth", inline: "nearest", block: "nearest" });
      } else if (segId < state.currentTransportIndex) {
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

  // --- Layer Tab Switching (L4 vs L7) ---
  function switchLayer(layer) {
    state.activeLayer = layer;
    if (layer === "application") {
      elements.tabLayerApp.classList.add("active");
      elements.tabLayerTransport.classList.remove("active");
      elements.viewLayerApp.classList.add("active");
      elements.viewLayerTransport.classList.remove("active");
    } else {
      elements.tabLayerTransport.classList.add("active");
      elements.tabLayerApp.classList.remove("active");
      elements.viewLayerTransport.classList.add("active");
      elements.viewLayerApp.classList.remove("active");
    }
    // Inform server so auto-play ticks in the right layer
    sendWS("switch_layer", { params: { layer } });
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
    // Layer Switcher Tabs
    elements.tabLayerApp.addEventListener("click", () => switchLayer("application"));
    elements.tabLayerTransport.addEventListener("click", () => switchLayer("transport"));

    // Cross-layer Jump Buttons
    elements.btnJumpToTransport.addEventListener("click", () => {
      switchLayer("transport");
      if (state.currentStepData && state.currentStepData.transport_segment_ids.length > 0) {
        const targetId = state.currentStepData.transport_segment_ids[0];
        const seg = state.transportSegments.find((s) => s.id === targetId);
        if (seg) {
          state.currentTransportSegment = seg;
          state.currentTransportIndex = seg.id;
          renderTransportDetail(seg);
          updateTransportStepperHighlight();
        }
      }
    });

    elements.btnJumpToApp.addEventListener("click", () => {
      switchLayer("application");
      if (state.currentTransportSegment && state.currentTransportSegment.application_event_id) {
        sendWS("seek", { target_step: state.currentTransportSegment.application_event_id });
      }
    });

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
      updateActivityStatus("browsing", "Connecting to DNS, TCP & HTTP...", "active");

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
      updateActivityStatus("mail", "Initializing TCP Handshake (Port 25) & SMTP...", "active");

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
      updateActivityStatus("streaming", "Connecting to CDN over TCP...", "active");
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
      sendWS("prev_step", { params: { layer: state.activeLayer } });
    });

    elements.btnNextStep.addEventListener("click", () => {
      sendWS("next_step", { params: { layer: state.activeLayer } });
    });

    elements.btnReplay.addEventListener("click", () => {
      sendWS("replay");
    });

    // Dock Tab Switcher
    document.querySelectorAll(".dock-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        const targetDock = tab.dataset.dock;
        document.querySelectorAll(".dock-tab").forEach((t) => t.classList.remove("active"));
        document.querySelectorAll(".dock-pane").forEach((p) => p.classList.remove("active"));
        tab.classList.add("active");
        const targetPane = document.getElementById(`pane-${targetDock}`);
        if (targetPane) targetPane.classList.add("active");
      });
    });

    // Network Conditions: Simulate Loss Toggle
    elements.checkboxSimulateLoss.addEventListener("change", (e) => {
      const isChecked = e.target.checked;
      state.simulateLoss = isChecked;
      elements.lossToggleLabel.innerHTML = `Simulate Packet Drop &amp; Retransmission: <strong>${isChecked ? "Enabled" : "Disabled"}</strong>`;
      sendWS("toggle_loss", { simulate_loss: isChecked });
    });

    // Copy Payloads
    elements.btnCopyWire.addEventListener("click", () => {
      const text = elements.wireCode.textContent;
      navigator.clipboard.writeText(text).then(() => {
        const original = elements.btnCopyWire.textContent;
        elements.btnCopyWire.textContent = "Copied!";
        setTimeout(() => { elements.btnCopyWire.textContent = original; }, 1500);
      });
    });

    elements.btnCopyTransportWire.addEventListener("click", () => {
      const text = elements.transportWireCode.textContent;
      navigator.clipboard.writeText(text).then(() => {
        const original = elements.btnCopyTransportWire.textContent;
        elements.btnCopyTransportWire.textContent = "Copied!";
        setTimeout(() => { elements.btnCopyTransportWire.textContent = original; }, 1500);
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
