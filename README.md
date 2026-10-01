# Computer Networks Laboratory: Dual-Panel Activity, Application & Transport Layer Protocol Visualizer

An interactive, educational web dashboard designed for **Computer Networks (Layer 4 & Layer 7)** course projects. It visually bridges everyday user interactions (**Web Browsing**, **Email Dispatch**, and **Adaptive Video Streaming**) with their real, RFC-compliant protocol exchanges:
* **Application Layer (Layer 7)**: DNS (RFC 1035), HTTP/1.1 (RFC 9112), SMTP (RFC 5321), and HLS (RFC 8216).
* **Transport Layer (Layer 4)**: TCP 3-Way Handshake, Sequence/ACK Arithmetic (RFC 793 / RFC 9293), Flow Control Receive Window, 10-State Machine, 4-Way Teardown, UDP comparison, and educational QUIC overview.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Client Browser                                    │
│  ┌───────────────────────────────┐     ┌─────────────────────────────────┐  │
│  │    LEFT: Activity Panel       │     │  RIGHT: Dual-Layer Visualizer   │  │
│  │  - Browsing (URL, Visit)      │     │  ┌───────────────────────────┐  │  │
│  │  - Mail (To, Subject, Body)   │     │  │ [APP LAYER]   [TRANS LAYER]│ │  │
│  │  - Streaming (Play, Quality)  │     │  └───────────────────────────┘  │  │
│  │  - Activity Log & Status      │     │  - TCP State (ESTABLISHED)      │  │
│  └──────────────┬────────────────┘     │  - Direction Diagram (C ──▶ S)  │  │
│                 │                      │  - Key Fields & Wire ASCII      │  │
│                 │ Activity Action      │  - Telemetry & cwnd Model       │  │
│                 │ (start_activity)     └────────────────▲────────────────┘  │
└─────────────────┼───────────────────────────────────────┼───────────────────┘
                  │                                       │
                  │ WebSocket Connection (/ws)            │
                  ▼                                       │
┌─────────────────────────────────────────────────────────┴───────────────────┐
│                        FastAPI Server (Python 3.13+)                        │
│                                                                             │
│  ┌──────────────────────────────┐     ┌──────────────────────────────────┐  │
│  │      main.py (FastAPI)       │     │     websocket_manager.py         │  │
│  │  - Serves static assets & UI │◄───►│  - Connection lifecycle          │  │
│  │  - Manages /ws endpoint      │     │  - Session state (step, playing) │  │
│  └──────────────┬───────────────┘     │  - Bidirectional sync coordinator│  │
│                 │                     └─────────────────▲────────────────┘  │
│                 ├── Generates L7                        │                   │
│                 ▼                                       │                   │
│  ┌──────────────────────────────┐                       │ Streams           │
│  │   protocol_simulator.py      │                       │ Coordinated Steps │
│  │  - DNS query/response gen    │                       │                   │
│  │  - HTTP/1.1 transaction gen  │                       │                   │
│  │  - SMTP state machine gen    │                       │                   │
│  └──────────────┬───────────────┘                       │                   │
│                 │ Passes App Steps                      │                   │
│                 ▼                                       │                   │
│  ┌──────────────────────────────┐                       │                   │
│  │   transport_simulator.py     │───────────────────────┘                   │
│  │  - TCP 3-Way Handshake       │                                           │
│  │  - Exact Seq/Ack Arithmetic  │                                           │
│  │  - 10-State Connection FSM   │                                           │
│  │  - 4-Way Teardown (FIN/ACK)  │                                           │
│  │  - Fault/Loss Simulation     │                                           │
│  └──────────────────────────────┘                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Assignment 2: Transport Layer Features

### 1. Dual-Layer Visualization (Right Panel Tabs)
The Right Panel features two synchronized views representing the **same** user interaction:
- **`[ 🌐 APPLICATION LAYER ]`**: Shows DNS queries, HTTP GET request/response, SMTP commands (EHLO, MAIL FROM, RCPT TO, DATA), and HLS playlists.
- **`[ ⚡ TRANSPORT LAYER ]`**: Visualizes the underlying TCP byte stream, 3-way handshake, payload segmentation, sequence/ACK progression, window advertisements, and connection teardown.

### 2. TCP 3-Way Handshake (RFC 793)
- **Segment 1 (Client &rarr; Server)**: `[SYN] Seq=1000 Ack=0 Win=64240`. Client transitions from `CLOSED` &rarr; `SYN-SENT`.
- **Segment 2 (Server &rarr; Client)**: `[SYN, ACK] Seq=5000 Ack=1001 Win=64240`. Server synchronizes sequence numbers, acknowledging the client's SYN (`1000 + 1`).
- **Segment 3 (Client &rarr; Server)**: `[ACK] Seq=1001 Ack=5001 Win=64240`. Client confirms server ISN. Both endpoints enter `ESTABLISHED`.

### 3. Exact Sequence and Acknowledgement Arithmetic Engine
- **SYN Flag**: Consumes exactly 1 sequence number (`Ack = Seq + 1`).
- **FIN Flag**: Consumes exactly 1 sequence number (`Ack = Seq + 1`).
- **Data Segments**: Advance sequence numbers strictly according to byte payload length (`Next_Seq = Seq + Payload_Length`).
- **Cumulative ACKs**: Acknowledge the next continuous byte expected by the receiver (`Ack = Seq + Length`).
- No arbitrary or randomized numbers are used; all values are mathematically verified.

### 4. TCP 10-State Connection Machine
The simulator models all standardized TCP states:
`CLOSED`, `LISTEN`, `SYN-SENT`, `SYN-RECEIVED`, `ESTABLISHED`, `FIN-WAIT-1`, `FIN-WAIT-2`, `CLOSE-WAIT`, `LAST-ACK`, and `TIME-WAIT`.
Live state indicators display the instantaneous status for both Client and Server.

### 5. TCP 4-Way Connection Teardown
- **Segment 1 (Client &rarr; Server)**: `[FIN, ACK]` &rarr; Client enters `FIN-WAIT-1`.
- **Segment 2 (Server &rarr; Client)**: `[ACK]` &rarr; Server enters `CLOSE-WAIT`, Client enters `FIN-WAIT-2`.
- **Segment 3 (Server &rarr; Client)**: `[FIN, ACK]` &rarr; Server enters `LAST-ACK`.
- **Segment 4 (Client &rarr; Server)**: `[ACK]` &rarr; Client enters `TIME-WAIT` (2 MSL timer), Server enters `CLOSED`.

### 6. Activity Mappings
- **Web Browsing**: DNS over UDP port 53 &rarr; TCP Handshake &rarr; HTTP GET carried over TCP (`PSH, ACK`) &rarr; Server ACK &rarr; HTTP 200 delivered over TCP &rarr; Client ACK &rarr; 4-way Teardown.
- **Electronic Mail**: TCP Handshake to port 25 &rarr; SMTP dialogue transported sequentially across the TCP byte stream (`220`, `EHLO`, `MAIL FROM`, `RCPT TO`, `DATA`, `MIME body`, `QUIT`) &rarr; Teardown.
- **Streaming Media**: DNS over UDP &rarr; Handshake &rarr; Manifest downloads &rarr; Media segment download split into consecutive Maximum Segment Size (MSS 1460B) chunks with cumulative ACKs.

### 7. Bidirectional Application &harr; Transport Synchronization
- Every `TransportSegment` maintains an `application_event_id` referencing the corresponding Application Step.
- Every `ProtocolStep` maintains a list of `transport_segment_ids`.
- In the UI:
  - Clicking an Application Step displays its underlying transport segments with a 1-click jump button.
  - Clicking any Transport Segment displays the associated Application message with a 1-click jump button.

### 8. Educational Analysis Tools
- **Congestion Window (cwnd) Graph**: Visualizes exponential growth during **Slow Start** (`1 -> 2 -> 4 -> 8 MSS`) transitioning to linear growth in **Congestion Avoidance** (`+1 MSS / RTT`). *(Clearly labeled: Simplified educational model)*.
- **TCP vs. UDP Reference Table**: Contrasts connection-oriented vs connectionless, ordering, reliability, header sizes, and use cases.
- **QUIC / HTTP/3 Overview**: Explains how modern protocols leverage UDP to eliminate head-of-line blocking and achieve 0-RTT handshakes.
- **Simulated Packet Loss & Recovery**: Toggleable fault simulator demonstrating how lost segments trigger Retransmission Timeouts (RTO) and duplicate sequence recovery.

---

## Playback Controls

The toolbar controls both Application and Transport views in lockstep:
- **⏸ Pause**: Freezes progression to inspect packet headers and states.
- **▶ Resume**: Continues automated progression (1.3s interval).
- **◀ Prev**: Decrements one step backward.
- **Next ▶**: Advances exactly one step forward.
- **⏮ Replay**: Resets session to Step 1 and restarts auto-play.
- **Timeline Scrubbing**: Click any node on either the Application or Transport stepper to navigate directly.

---

## Project Structure

```
network-visualizer/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application & WebSocket router
│   ├── protocol_models.py          # Pydantic data schemas (L4 & L7 events, stats)
│   ├── protocol_simulator.py       # Application layer generators (DNS, HTTP, SMTP, HLS)
│   ├── transport_simulator.py      # TCP connection simulator, seq/ack math & state machine
│   ├── websocket_manager.py        # WebSocket controller with synchronized cross-layer streaming
│   ├── templates/
│   │   └── index.html              # Dual-panel semantic HTML5 with layer switcher tabs
│   └── static/
│       ├── style.css               # Responsive styles, TCP flags, state pills, cwnd chart
│       └── app.js                  # Vanilla JS WebSocket client, tab switcher, sync manager
├── tests/
│   ├── __init__.py
│   ├── test_protocol_simulator.py  # Assignment 1 test suite (Application Layer)
│   └── test_transport_simulator.py # Assignment 2 test suite (Transport Layer & Synchronization)
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Setup & Running Instructions

### 1. Virtual Environment & Dependencies
```bash
cd /Users/ayushchauhan/.gemini/antigravity/scratch/network-visualizer

# Activate Python 3.13 virtual environment
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Run Automated Test Suite
```bash
pytest tests/ -v
```
All **15 automated tests** execute in under 0.2 seconds, validating:
- Application Layer: Browsing, Mail, Streaming, factory utilities, and web endpoints.
- Transport Layer: TCP Handshake, Seq/Ack arithmetic, state machine transitions, 4-way teardown, HTTP-over-TCP, SMTP-over-TCP, HLS segmentation, fault injection, and WebSocket synchronization.

### 3. Launch the Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Open your browser at:
**`http://127.0.0.1:8000`**

---

## Educational Disclaimers & Assumptions

1. **Deterministic Simulation**: All TCP sequence numbers, acknowledgements, and states are generated deterministically according to RFC 793 and RFC 9293 specifications. This application does not bind to raw network sockets or capture live OS network adapters, ensuring 100% reliable execution in restrictive lab/firewall environments.
2. **Simplified Congestion Control**: The cwnd visualization demonstrates standard textbook Tahoe/Reno concepts (Slow Start & Congestion Avoidance) for pedagogical clarity, without implementing complex kernel-level loss-recovery heuristics (BBR, CUBIC).
3. **Layer Abstraction**: The simulator explicitly focuses on Layer 4 and Layer 7 dialogue. Lower layers (IP framing, ARP, Ethernet preamble) are omitted to focus student attention on transport-layer mechanisms.

---

## AI-Assisted Development Notes
This project was developed with the assistance of Antigravity AI pair programming, focusing on rigorous RFC compliance, clean decoupled Python architecture, and student-accessible visualization.
