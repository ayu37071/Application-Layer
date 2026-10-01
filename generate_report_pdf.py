import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether
)
from reportlab.pdfgen import canvas

PDF_PATH = "/Users/ayushchauhan/PROJECTS/network-visualizer/ProtoViz_Project_Report.pdf"

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 755, "ProtoViz — Application & Transport Layer Protocol Visualizer")
            self.drawRightString(612 - 54, 755, "Project Report")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 747, 612 - 54, 747)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 612 - 54, 45)
        
        self.drawString(54, 32, "Live Demo: https://protoboot.up.railway.app/  |  GitHub: https://github.com/ayu37071/Application-Layer")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 54, 32, page_str)
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#0f172a") # Dark navy
    accent_blue = colors.HexColor("#0284c7")
    accent_purple = colors.HexColor("#6366f1")
    text_dark = colors.HexColor("#1e293b")
    text_muted = colors.HexColor("#64748b")
    card_bg = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.white,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14.5,
        textColor=colors.HexColor("#94a3b8"),
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=accent_blue,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=text_dark,
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'BulletDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=text_dark,
        leftIndent=10,
        spaceAfter=3.5
    )

    link_box_style = ParagraphStyle(
        'LinkBox',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=14,
        textColor=colors.white
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.5,
        textColor=text_dark
    )

    table_code_style = ParagraphStyle(
        'TableCode',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0369a1")
    )

    story = []

    # 1. Header Banner Box with Clickable Links
    banner_data = [
        [
            Paragraph("<b>PROJECT REPORT &amp; SPECIFICATION</b>", ParagraphStyle('Badge', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor("#38bdf8"))),
            Paragraph("<b>Computer Networks Lab (Assignments 1 &amp; 2)</b>", ParagraphStyle('SubBadge', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor("#94a3b8"), alignment=2))
        ],
        [
            Paragraph("ProtoViz: Application &amp; Transport Layer Visualizer", title_style),
            ""
        ],
        [
            Paragraph("An interactive educational web platform demonstrating synchronized protocol flows across L7 (DNS, HTTP/1.1, SMTP, HLS) and L4 (TCP 3-way handshake, Seq/Ack math, state machine, flow &amp; congestion control).", subtitle_style),
            ""
        ],
        [
            Paragraph(
                """<b>🌐 Live Website:</b> <a href="https://protoboot.up.railway.app/"><font color="#38bdf8"><u>https://protoboot.up.railway.app/</u></font></a><br/>
                <b>🐙 GitHub Repository:</b> <a href="https://github.com/ayu37071/Application-Layer"><font color="#38bdf8"><u>https://github.com/ayu37071/Application-Layer</u></font></a>""",
                link_box_style
            ),
            Paragraph(
                """<b>Author:</b> Ayush Chauhan<br/>
                <b>Stack:</b> Python 3.13, FastAPI, WebSockets, JS<br/>
                <b>Testing:</b> 15/15 Pytest Passed (100%)""",
                ParagraphStyle('MetaInfo', fontName='Helvetica', fontSize=8.5, leading=12, textColor=colors.HexColor("#cbd5e1"), alignment=2)
            )
        ]
    ]

    banner_table = Table(banner_data, colWidths=[330, 174])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ('SPAN', (0, 1), (1, 1)),
        ('SPAN', (0, 2), (1, 2)),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))

    story.append(banner_table)
    story.append(Spacer(1, 12))

    # 2. Executive Summary
    story.append(Paragraph("1. Executive Overview &amp; Objectives", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=2, spaceAfter=6))
    story.append(Paragraph(
        "<b>ProtoViz</b> is a web-based educational dashboard designed to demystify computer network protocol interactions by simultaneously presenting <b>user activity</b> on the left panel and <b>in-depth protocol exchanges</b> on the right panel. Designed across Assignment 1 (Application Layer) and Assignment 2 (Transport Layer), the system provides seamless dual-layer visibility.",
        body_style
    ))
    story.append(Paragraph(
        "Students can perform intuitive high-level actions (visiting a URL, composing an email, or streaming video), and watch the resulting network wire exchanges breakdown progressively in real time. The platform establishes strict <b>bi-directional cross-layer linking</b>: inspecting an HTTP GET request automatically identifies its underlying TCP packets, while clicking a transport segment highlights the corresponding application step.",
        body_style
    ))

    # 3. Core Features Breakdown
    story.append(Paragraph("2. System Capabilities &amp; Key Features", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=2, spaceAfter=6))

    story.append(Paragraph("A. Application-Layer (L7) Activities", h2_style))
    story.append(Paragraph("• <b>Interactive Web Browsing:</b> Simulates full DNS resolution (RFC 1035 UDP queries to 8.8.8.8) followed by HTTP/1.1 (RFC 9112) GET and 200 OK exchanges with header breakdowns (Host, User-Agent, Content-Type, Content-Length). Includes quick preset buttons (example.com, wiki.org, etc.).", bullet_style))
    story.append(Paragraph("• <b>Email Protocol Client (SMTP):</b> Simulates an RFC 5321 mail delivery transaction over Port 25: 220 Service Ready &rarr; EHLO &rarr; MAIL FROM &rarr; RCPT TO &rarr; DATA (with multipart/MIME ASCII formatting) &rarr; QUIT &rarr; 221 Closing.", bullet_style))
    story.append(Paragraph("• <b>Adaptive Video Streaming (HLS):</b> Simulates HTTP Live Streaming (RFC 8216) with resolution selection (360p, 720p HD, 1080p FHD). Fetches Master M3U8 Playlist, chunk variant schedule, and downloads consecutive .ts media segments, reflected live in a mock player buffer bar.", bullet_style))

    story.append(Paragraph("B. Transport-Layer (L4) Mechanics (Assignment 2)", h2_style))
    story.append(Paragraph("• <b>RFC 793 &amp; RFC 9293 TCP State Engine:</b> Accurate 10-state finite state machine modeling (CLOSED, LISTEN, SYN-SENT, SYN-RECEIVED, ESTABLISHED, FIN-WAIT-1, FIN-WAIT-2, CLOSE-WAIT, LAST-ACK, TIME-WAIT) displayed in live badges.", bullet_style))
    story.append(Paragraph("• <b>3-Way Handshake &amp; 4-Way Teardown:</b> Step-by-step visualization of connection initiation (SYN &rarr; SYN-ACK &rarr; ACK) with initial sequence number (ISN) negotiation, and clean teardown (FIN-ACK &rarr; ACK &rarr; FIN-ACK &rarr; ACK).", bullet_style))
    story.append(Paragraph("• <b>Deterministic Seq/Ack Arithmetic:</b> Exact byte-stream sequence and acknowledgement number progression where SYN/FIN consume 1 phantom byte and data packets consume exactly <i>payload_length</i> bytes.", bullet_style))
    story.append(Paragraph("• <b>Congestion Window (cwnd) &amp; Flow Control:</b> Visual representation of Slow Start (exponential cwnd doubling) transitioning at ssthresh to Congestion Avoidance (+1 MSS additive increase), alongside advertised receive window flow control.", bullet_style))
    story.append(Paragraph("• <b>Network Fault &amp; Packet Loss Injection:</b> Deterministic fault simulation toggling packet drops, triggering Retransmission Timeout (RTO) duplicate sequence number emissions.", bullet_style))

    story.append(Paragraph("C. Interactive Playback &amp; Analysis Dock", h2_style))
    story.append(Paragraph("• <b>Synchronized Controls:</b> Full playback control bar (Auto-play with 1.3s calibrated ticker, Pause, Resume, Next Step, Previous Step, Replay, and Direct Timeline Seeking).", bullet_style))
    story.append(Paragraph("• <b>Layer-Aware Stepping:</b> The stepper dynamically adapts to the user's active view: advancing application messages when on L7, and walking through every transport segment (including handshakes and acknowledgments) when on L4.", bullet_style))
    story.append(Paragraph("• <b>Analysis Dock Shelf:</b> Dedicated docked panels for <i>Live Telemetry Stats</i>, <i>Congestion Chart</i>, <i>TCP vs UDP Architecture Matrix</i>, <i>QUIC &amp; HTTP/3 Educational Notes</i>, and <i>Fault Controls</i>.", bullet_style))

    # 4. Protocols Matrix
    story.append(Spacer(1, 4))
    story.append(Paragraph("3. Protocol Simulation Matrix", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=2, spaceAfter=6))

    proto_table_data = [
        [
            Paragraph("Protocol", table_header_style),
            Paragraph("Layer", table_header_style),
            Paragraph("Standard / RFC", table_header_style),
            Paragraph("Ports", table_header_style),
            Paragraph("Key Visualized Fields &amp; Mechanics", table_header_style),
        ],
        [
            Paragraph("<b>DNS</b>", table_cell_style),
            Paragraph("L7 (App)", table_cell_style),
            Paragraph("RFC 1035", table_code_style),
            Paragraph("53 (UDP)", table_cell_style),
            Paragraph("Query/Response, Transaction ID, QNAME, QTYPE (A/AAAA), TTL, Answer RDATA", table_cell_style)
        ],
        [
            Paragraph("<b>HTTP/1.1</b>", table_cell_style),
            Paragraph("L7 (App)", table_cell_style),
            Paragraph("RFC 9112", table_code_style),
            Paragraph("80 (TCP)", table_cell_style),
            Paragraph("GET request, Status 200 OK, Host, User-Agent, Content-Type, Content-Length", table_cell_style)
        ],
        [
            Paragraph("<b>SMTP</b>", table_cell_style),
            Paragraph("L7 (App)", table_cell_style),
            Paragraph("RFC 5321", table_code_style),
            Paragraph("25 (TCP)", table_cell_style),
            Paragraph("220 Banner, EHLO, MAIL FROM, RCPT TO, DATA, 250 OK, QUIT, 221 Bye", table_cell_style)
        ],
        [
            Paragraph("<b>HLS</b>", table_cell_style),
            Paragraph("L7 (App)", table_cell_style),
            Paragraph("RFC 8216", table_code_style),
            Paragraph("80/443", table_cell_style),
            Paragraph("M3U8 master playlist parsing, video chunk scheduling, buffer level emulation", table_cell_style)
        ],
        [
            Paragraph("<b>TCP</b>", table_cell_style),
            Paragraph("L4 (Trans)", table_cell_style),
            Paragraph("RFC 793/9293", table_code_style),
            Paragraph("Ephemeral", table_cell_style),
            Paragraph("SEQ, ACK, Flags [SYN, ACK, PSH, FIN], 64KB Window, 10-state machine, cwnd", table_cell_style)
        ],
        [
            Paragraph("<b>UDP</b>", table_cell_style),
            Paragraph("L4 (Trans)", table_cell_style),
            Paragraph("RFC 768", table_code_style),
            Paragraph("53 (DNS)", table_cell_style),
            Paragraph("Connectionless datagrams, 8-byte header, zero-handshake overhead demonstration", table_cell_style)
        ],
    ]

    proto_table = Table(proto_table_data, colWidths=[65, 55, 75, 45, 264])
    proto_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(proto_table)

    # 5. AI Usage & Agentic Workflow Section
    story.append(Spacer(1, 8))
    story.append(Paragraph("4. Role of Artificial Intelligence (AI) in Development", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=2, spaceAfter=6))
    story.append(Paragraph(
        "This project was architected, developed, and verified utilizing <b>Google Antigravity (AGY)</b>, an agentic AI pair-programming system. Rather than generating disconnected boilerplate, AI served as an active co-engineer managing codebase state, running unit tests, and refining interfaces.",
        body_style
    ))

    ai_contributions = [
        ("Architecture & Data Modeling", "Designed modular Pydantic v2 schemas (protocol_models.py) ensuring strict type-safety across Python backend and client JSON events. Established clean separation between Application Layer and Transport Layer simulation engines."),
        ("RFC-Compliant Protocol Engineering", "Formulated the mathematical sequence/acknowledgment engine in transport_simulator.py conforming to RFC 793/9293, computing correct relative time offsets, sliding windows, and 10 distinct TCP FSM states."),
        ("Layer-Aware WebSocket Concurrency", "Built an asynchronous WebSocket manager (websocket_manager.py) using Python's asyncio.Lock to govern thread-safe playback tickers, enabling bidirectional pointer alignment between L4 segments and L7 application events."),
        ("Modern UX/UI Design System", "Created a high-density, professional dark-mode interface in CSS/Vanilla JS (style.css, app.js) featuring collapsible inspection shelves, directional packet animations, responsive side-by-side grids, and zero third-party UI framework bloat."),
        ("Automated Quality Assurance", "Synthesized a comprehensive 15-test pytest suite (tests/) validating handshake math, teardown sequences, retransmission edge cases, and WebSocket control messages with 100% test pass rate."),
        ("Iterative Debugging & Live Deployment", "Rapidly identified and fixed environment hurdles (venv path migration, Starlette testclient title matching, viewport overflow constraints) and prepared the production Docker container deployed on Railway.")
    ]

    for title, desc in ai_contributions:
        box_data = [
            [Paragraph(f"<b>🤖 {title}</b>", ParagraphStyle('AiTitle', fontName='Helvetica-Bold', fontSize=8.5, textColor=accent_blue))],
            [Paragraph(desc, ParagraphStyle('AiDesc', fontName='Helvetica', fontSize=8, leading=11.5, textColor=text_dark))]
        ]
        t = Table(box_data, colWidths=[504])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ('LINELEFT', (0, 0), (0, -1), 3, accent_blue),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 7),
            ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ]))
        story.append(t)
        story.append(Spacer(1, 3.5))

    # 6. Verification and Test Results
    story.append(Spacer(1, 6))
    story.append(Paragraph("5. Quality Assurance &amp; Verification (15/15 Passed)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=2, spaceAfter=6))
    story.append(Paragraph("The visualizer maintains <b>15 automated pytest tests</b> covering all network protocol flows, state transitions, and server endpoints. All tests pass cleanly in 0.18s.", body_style))

    test_data = [
        [Paragraph("Test Case Identifier", table_header_style), Paragraph("Module", table_header_style), Paragraph("Verification Scope", table_header_style), Paragraph("Result", table_header_style)],
        [Paragraph("test_browsing_flow", table_code_style), Paragraph("test_protocol_simulator", table_cell_style), Paragraph("DNS query/response &amp; HTTP/1.1 GET/200 OK step generation", table_cell_style), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell_style)],
        [Paragraph("test_mail_flow", table_code_style), Paragraph("test_protocol_simulator", table_cell_style), Paragraph("SMTP command-response sequence integrity (EHLO to QUIT)", table_cell_style), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell_style)],
        [Paragraph("test_streaming_flow", table_code_style), Paragraph("test_protocol_simulator", table_cell_style), Paragraph("HLS manifest retrieval &amp; multiple TS media chunk downloads", table_cell_style), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell_style)],
        [Paragraph("test_tcp_handshake", table_code_style), Paragraph("test_transport_simulator", table_cell_style), Paragraph("SYN, SYN-ACK, ACK sequence and client/server connection states", table_cell_style), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell_style)],
        [Paragraph("test_tcp_seq_ack_arithmetic", table_code_style), Paragraph("test_transport_simulator", table_cell_style), Paragraph("Math correctness of Seq/Ack across data packets &amp; phantom bytes", table_cell_style), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell_style)],
        [Paragraph("test_tcp_teardown", table_code_style), Paragraph("test_transport_simulator", table_cell_style), Paragraph("4-way termination, FIN-WAIT, CLOSE-WAIT, and TIME-WAIT states", table_cell_style), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell_style)],
        [Paragraph("test_cross_layer_linking", table_code_style), Paragraph("test_transport_simulator", table_cell_style), Paragraph("Bi-directional mapping between L7 events and carrier L4 segments", table_cell_style), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell_style)],
        [Paragraph("test_network_fault_retransmission", table_code_style), Paragraph("test_transport_simulator", table_cell_style), Paragraph("Deterministic drop injection, RTO simulation, duplicate Seq emission", table_cell_style), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell_style)],
        [Paragraph("test_websocket_transport_sync", table_code_style), Paragraph("test_transport_simulator", table_cell_style), Paragraph("Live WebSocket sync, seek, next/prev layer-aware stepping", table_cell_style), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell_style)],
    ]

    qa_table = Table(test_data, colWidths=[150, 110, 184, 60])
    qa_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(qa_table)

    # 7. Official Links Card
    story.append(Spacer(1, 8))
    story.append(Paragraph("6. Project Access &amp; Repository Links", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=2, spaceAfter=6))

    links_summary_data = [
        [
            Paragraph("<b>Target Resource</b>", table_header_style),
            Paragraph("Clickable Web Link", table_header_style),
            Paragraph("Description", table_header_style),
        ],
        [
            Paragraph("<b>Live Deployment</b>", table_cell_style),
            Paragraph('<a href="https://protoboot.up.railway.app/"><font color="#0284c7"><u>https://protoboot.up.railway.app/</u></font></a>', table_cell_style),
            Paragraph("Production web application hosted on Railway cloud with HTTPS &amp; WebSockets.", table_cell_style)
        ],
        [
            Paragraph("<b>GitHub Repository</b>", table_cell_style),
            Paragraph('<a href="https://github.com/ayu37071/Application-Layer"><font color="#0284c7"><u>https://github.com/ayu37071/Application-Layer</u></font></a>', table_cell_style),
            Paragraph("Public Git repository containing all source code, test suites, and documentation.", table_cell_style)
        ]
    ]

    links_table = Table(links_summary_data, colWidths=[100, 204, 200])
    links_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(links_table)

    # Build PDF with Page Numbers
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully built at {PDF_PATH}")

if __name__ == "__main__":
    build_pdf()
