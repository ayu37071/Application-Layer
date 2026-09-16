# Application Layer Activity & Protocol Visualizer

An interactive, educational web dashboard designed for **Computer Networks – Application Layer (Layer 7)** course projects. It visually bridges everyday user interactions (**Web Browsing**, **Email Dispatch**, and **Adaptive Video Streaming**) with their real, RFC-compliant protocol exchanges (**DNS**, **HTTP/1.1**, **SMTP**, and **HLS**) through real-time progressive WebSocket synchronization.

---

## Architecture Overview

The system strictly follows a decoupled **two-panel architecture**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Client Browser                                    │
│  ┌───────────────────────────────┐     ┌─────────────────────────────────┐  │
│  │    LEFT: Activity Panel       │     │  RIGHT: Protocol Visualizer     │  │
│  │  - Browsing (URL, Visit)      │     │  - Playback Bar (⏮ ◀ ⏸ ▶ ⏭)     │  │
│  │  - Mail (To, Subject, Body)   │     │  - Direction Diagram (C ──▶ S)  │  │
│  │  - Streaming (Play, Quality)  │     │  - Key Fields & Raw Wire Data   │  │
│  │  - Activity Log & Status      │     │  - Cumulative Step Timeline     │  │
│  └──────────────┬────────────────┘     └────────────────▲────────────────┘  │
│                 │                                       │                   │
│                 │ Activity Action                       │ Step Updates &    │
│                 │ (start_activity)                      │ State Sync        │
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
│  └──────────────┬───────────────┘     │  - Playback loop (asyncio timer) │  │
│                 │                     └─────────────────▲────────────────┘  │
│                 │ Invokes                               │ Streams           │
│                 ▼                                       │ Generated Steps   │
│  ┌──────────────────────────────┐     ┌─────────────────┴────────────────┐  │
│  │   protocol_simulator.py      │     │      protocol_models.py          │  │
│  │  - DNS query/response gen    │────►│  - ProtocolStep, Direction       │  │
│  │  - HTTP/1.1 transaction gen  │     │  - HighlightField, SessionState  │  │
│  │  - SMTP state machine gen    │     │  - WSClientMessage & WSServerMsg │  │
│  │  - HLS manifest & chunks gen │     └──────────────────────────────────┘  │
│  └──────────────────────────────┘                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### UI Layout
- **Left Panel (Activity Panel)**: Provides interactive forms for the 3 activities, live status badges, preset suggestions, and a scrolling activity event log.
- **Right Panel (Protocol Visualization Panel)**: Displays animated packet directions (`Client ──▶ Server` or `Server ──▶ Client`), sequence numbering, millisecond timing offsets, parsed key fields (Status codes, Transaction IDs, URIs), wire-accurate ASCII payloads, and educational explanations.

On screens under 1100px width, the panels seamlessly stack vertically for mobile and tablet responsiveness.

---

## Supported Application Layer Flows

### 1. Web Browsing Flow (DNS + HTTP/1.1)
Demonstrates the two-stage process required to fetch a webpage:
1. **Step 1 — DNS Query (`Client ──▶ DNS Server:53`)**: Standard UDP query asking for the IPv4 (A record) of the requested domain, with Transaction ID and Recursion Desired (`0x0100`).
2. **Step 2 — DNS Response (`DNS Server:53 ──▶ Client`)**: Returns the resolved IPv4 address, TTL cache duration (300 seconds), and NoError status code.
3. **Step 3 — HTTP GET Request (`Client ──▶ Web Server:80`)**: RFC 9112 HTTP/1.1 GET request featuring `Host`, `User-Agent`, `Accept`, and `Connection: keep-alive` headers.
4. **Step 4 — HTTP 200 OK Response (`Web Server:80 ──▶ Client`)**: HTTP/1.1 response delivering headers (`Content-Type: text/html`, `Content-Length`) and the HTML entity body.

### 2. Electronic Mail Flow (SMTP - RFC 5321)
Demonstrates the classic 13-step client-server dialog over TCP port 25:
1. `220` Service Ready greeting from MTA.
2. `EHLO client.fqdn` from client.
3. `250` Multi-line response listing server ESMTP extensions (`PIPELINING`, `SIZE`, `8BITMIME`).
4. `MAIL FROM:<sender>` envelope sender declaration.
5. `250 2.1.0` Sender OK response.
6. `RCPT TO:<recipient>` envelope recipient declaration.
7. `250 2.1.5` Recipient OK response.
8. `DATA` request to transition from envelope to message content.
9. `354` Start mail input instructions (`end with <CRLF>.<CRLF>`).
10. MIME headers (`From`, `To`, `Subject`, `Message-ID`, `Date`), blank separator, message body, and terminal period (`.`).
11. `250 2.0.0` Queued confirmation with internal spool ID.
12. `QUIT` orderly termination command.
13. `221 2.0.0` Bye closing transmission channel.

### 3. Adaptive Video Streaming Flow (HLS Paradigm)
Demonstrates chunk-based media delivery over standard HTTP:
1. DNS Query for CDN hostname (`cdn.streamnet.tv`).
2. DNS Response returning CDN edge node IP.
3. HTTP GET for `master.m3u8` master manifest.
4. HTTP 200 OK returning master manifest with multiple bitrate streams (`#EXT-X-STREAM-INF` for 360p, 720p, and 1080p).
5. HTTP GET for media variant playlist (`720p/playlist.m3u8`).
6. HTTP 200 OK returning 4-second video chunk list (`#EXTINF:4.000, segment_1042.ts`).
7. HTTP GET for initial segment (`segment_1042.ts`).
8. HTTP 200 OK delivering MPEG-TS chunk (~1.2 MB).
9. HTTP GET for subsequent segment (`segment_1043.ts`).
10. HTTP 200 OK delivering MPEG-TS chunk while updating buffer health.

---

## Interactive Playback Controls

The toolbar in the Protocol Visualization Panel allows full temporal navigation:
- **⏸ Pause**: Halts the automatic step ticker so students can inspect packet details at their own pace.
- **▶ Resume**: Continues automated progression from the current step.
- **◀ Prev**: Decrements the sequence pointer to inspect previous packets.
- **Next ▶**: Advances exactly one step forward.
- **⏮ Replay**: Rewinds the exchange to Step 1 and restarts automatic playback.
- **Interactive Timeline**: Click any node in the top stepper bar to jump directly to that protocol step.

---

## Project Structure

```
network-visualizer/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application & WebSocket router
│   ├── protocol_models.py          # Pydantic data schemas for steps & WS messages
│   ├── protocol_simulator.py       # Deterministic RFC-accurate protocol engines
│   ├── websocket_manager.py        # Connection manager & interactive playback ticker
│   ├── templates/
│   │   └── index.html              # Clean semantic HTML5 (strict 2-panel layout)
│   └── static/
│       ├── style.css               # Responsive design, directional animations, dark-tech theme
│       └── app.js                  # Vanilla JS WebSocket client & dynamic DOM visualizer
├── tests/
│   ├── __init__.py
│   └── test_protocol_simulator.py  # Pytest suite for all 3 flows and WebSocket lifecycle
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Setup & Running Instructions

### Prerequisites
- Python 3.13+ installed (managed via `uv` or system Python)

### 1. Virtual Environment & Dependencies
```bash
# Clone or navigate to the project directory
cd /Users/ayushchauhan/.gemini/antigravity/scratch/network-visualizer

# Create a virtual environment using Python 3.13
uv venv --python 3.13 .venv

# Activate the virtual environment
source .venv/bin/activate

# Install requirements
uv pip install -r requirements.txt
```

### 2. Run the Automated Test Suite
```bash
pytest tests/test_protocol_simulator.py -v
```
All 6 tests verify protocol sequence integrity, RFC keywords, HTTP endpoints, and WebSocket transitions.

### 3. Start the Web Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## Student Viva & Presentation Notes

When presenting this project to your instructor, highlight these key design principles:

1. **Layer 7 Focus**: Lower layer handshakes (TCP 3-way handshake `SYN, SYN-ACK, ACK`, TLS 1.3 key exchange, IP routing) occur transparently beneath the application layer. By focusing on Layer 7, students observe exact ASCII protocol grammar (HTTP verbs, SMTP reply codes, DNS resource records) without packet fragmentation noise.
2. **Deterministic Simulation vs. Live Sockets**: Real-world SMTP traffic over port 25 is actively filtered by residential and university ISPs to prevent spam. Simulation ensures 100% reliable, reproducible classroom demonstrations while remaining RFC-accurate.
3. **Adaptive Bitrate Streaming (ABR)**: Explaining why modern video services use HTTP (HLS/DASH) rather than raw UDP streaming highlights that HTTP seamlessly passes through NATs, firewalls, and leverages existing web caching infrastructure.
# Application-Layer
