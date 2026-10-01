"""
Publication-Quality PDF Documentation Generator
Application Layer Activity & Protocol Visualizer
- Clickable Hyperlinks (GitHub & Live Railway Website)
- High-contrast visual styling (headers, cards, tables, code blocks)
- Setup & execution instructions
- Full RFC protocol architecture overview & Viva notes
"""

import os
import sys

class PDFBuilder:
    def __init__(self, filename="Application_Layer_Visualizer_Guide.pdf", page_width=595.28, page_height=841.89):
        # A4 standard dimensions in PostScript points (595.28 x 841.89 pt)
        self.filename = filename
        self.page_width = page_width
        self.page_height = page_height
        self.pages = []
        self.current_page = None
        self.total_pages = 0

    def new_page(self):
        page = {
            "stream": [],
            "links": []
        }
        self.pages.append(page)
        self.current_page = page
        self.total_pages = len(self.pages)
        return page

    def add_link(self, rect, uri):
        """Add clickable URI annotation. rect = (x1, y1, x2, y2) in bottom-left origin points."""
        if self.current_page is not None:
            self.current_page["links"].append((rect, uri))

    def raw_stream(self, s):
        if self.current_page:
            self.current_page["stream"].append(s)

    def rect(self, x, y, w, h, fill_rgb=None, stroke_rgb=None, stroke_width=1):
        cmds = ["q"]
        if stroke_rgb:
            r, g, b = stroke_rgb
            cmds.append(f"{r:.3f} {g:.3f} {b:.3f} RG")
            cmds.append(f"{stroke_width} w")
        if fill_rgb:
            r, g, b = fill_rgb
            cmds.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
        
        cmds.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re")
        
        if fill_rgb and stroke_rgb:
            cmds.append("B")
        elif fill_rgb:
            cmds.append("f")
        elif stroke_rgb:
            cmds.append("S")
        cmds.append("Q")
        self.raw_stream("\n".join(cmds) + "\n")

    def rounded_rect(self, x, y, w, h, r=4, fill_rgb=None, stroke_rgb=None, stroke_width=1):
        k = 0.552284749831 * r
        cmds = ["q"]
        if stroke_rgb:
            sr, sg, sb = stroke_rgb
            cmds.append(f"{sr:.3f} {sg:.3f} {sb:.3f} RG")
            cmds.append(f"{stroke_width} w")
        if fill_rgb:
            fr, fg, fb = fill_rgb
            cmds.append(f"{fr:.3f} {fg:.3f} {fb:.3f} rg")
        
        cmds.append(f"{x + r:.2f} {y:.2f} m")
        cmds.append(f"{x + w - r:.2f} {y:.2f} l")
        cmds.append(f"{x + w - r + k:.2f} {y:.2f} {x + w:.2f} {y + r - k:.2f} {x + w:.2f} {y + r:.2f} c")
        cmds.append(f"{x + w:.2f} {y + h - r:.2f} l")
        cmds.append(f"{x + w:.2f} {y + h - r + k:.2f} {x + w - r + k:.2f} {y + h:.2f} {x + w - r:.2f} {y + h:.2f} c")
        cmds.append(f"{x + r:.2f} {y + h:.2f} l")
        cmds.append(f"{x + r - k:.2f} {y + h:.2f} {x:.2f} {y + h - r + k:.2f} {x:.2f} {y + h - r:.2f} c")
        cmds.append(f"{x:.2f} {y + r:.2f} l")
        cmds.append(f"{x:.2f} {y + r - k:.2f} {x + r - k:.2f} {y:.2f} {x + r:.2f} {y:.2f} c")
        cmds.append("h")
        
        if fill_rgb and stroke_rgb:
            cmds.append("B")
        elif fill_rgb:
            cmds.append("f")
        elif stroke_rgb:
            cmds.append("S")
        cmds.append("Q")
        self.raw_stream("\n".join(cmds) + "\n")

    def line(self, x1, y1, x2, y2, stroke_rgb=(0.7, 0.7, 0.7), stroke_width=1):
        r, g, b = stroke_rgb
        cmd = f"q {r:.3f} {g:.3f} {b:.3f} RG {stroke_width} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S Q\n"
        self.raw_stream(cmd)

    def escape_text(self, text):
        replacements = {
            "\\": "\\\\",
            "(": "\\(",
            ")": "\\)",
            "•": "\x95",
            "✓": "[OK]",
            "—": "--",
            "–": "-",
            "→": "->",
            "←": "<-",
            "↔": "<->",
            "“": "\"",
            "”": "\"",
            "‘": "'",
            "’": "'",
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text

    def draw_text(self, x, y, text, font="F1", size=10, rgb=(0, 0, 0)):
        r, g, b = rgb
        esc = self.escape_text(text)
        cmd = f"BT /{font} {size} Tf {r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} Td ({esc}) Tj ET\n"
        self.raw_stream(cmd)

    def build_pdf(self):
        buf = bytearray()
        buf.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        
        offsets = {}
        
        def new_object(obj_num, data):
            offsets[obj_num] = len(buf)
            buf.extend(f"{obj_num} 0 obj\n".encode("latin1"))
            buf.extend(data)
            buf.extend(b"\nendobj\n")

        font_map = {
            "F1": ("Helvetica", 3),
            "F2": ("Helvetica-Bold", 4),
            "F3": ("Courier", 5),
            "F4": ("Courier-Bold", 6),
            "F5": ("Helvetica-Oblique", 7),
        }
        
        next_obj = 8
        page_obj_nums = []
        page_content_nums = []
        page_annot_obj_ids = []

        for p_idx, page in enumerate(self.pages):
            p_obj = next_obj
            c_obj = next_obj + 1
            next_obj += 2
            page_obj_nums.append(p_obj)
            page_content_nums.append(c_obj)
            
            annots = []
            for link in page["links"]:
                annots.append(next_obj)
                next_obj += 1
            page_annot_obj_ids.append(annots)

        # 1: Catalog
        new_object(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        
        # 2: Pages
        kids_str = " ".join([f"{num} 0 R" for num in page_obj_nums])
        pages_dict = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_nums)} >>".encode("latin1")
        new_object(2, pages_dict)

        # Fonts (Standard 14 PDF Type1)
        for font_alias, (font_name, f_num) in font_map.items():
            f_dict = f"<< /Type /Font /Subtype /Type1 /BaseFont /{font_name} /Encoding /WinAnsiEncoding >>".encode("latin1")
            new_object(f_num, f_dict)

        # Page, Annotations & Content objects
        for idx, page in enumerate(self.pages):
            p_num = page_obj_nums[idx]
            c_num = page_content_nums[idx]
            ann_nums = page_annot_obj_ids[idx]

            for l_idx, (rect, uri) in enumerate(page["links"]):
                l_num = ann_nums[l_idx]
                x1, y1, x2, y2 = rect
                esc_uri = uri.replace("(", "\\(").replace(")", "\\)")
                annot_dict = (
                    f"<< /Type /Annot /Subtype /Link\n"
                    f"   /Rect [{x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f}]\n"
                    f"   /Border [0 0 0]\n"
                    f"   /H /I\n"
                    f"   /A << /Type /Action /S /URI /URI ({esc_uri}) >>\n"
                    f">>"
                ).encode("latin1")
                new_object(l_num, annot_dict)

            annots_ref_str = " ".join([f"{num} 0 R" for num in ann_nums])
            fonts_ref_str = " ".join([f"/{k} {v[1]} 0 R" for k, v in font_map.items()])
            page_dict = (
                f"<< /Type /Page\n"
                f"   /Parent 2 0 R\n"
                f"   /MediaBox [0 0 {self.page_width:.2f} {self.page_height:.2f}]\n"
                f"   /Resources << /Font << {fonts_ref_str} >> >>\n"
                f"   /Contents {c_num} 0 R\n"
                f"   /Annots [{annots_ref_str}]\n"
                f">>"
            ).encode("latin1")
            new_object(p_num, page_dict)

            stream_data = "".join(page["stream"]).encode("latin1", errors="replace")
            content_dict = (
                f"<< /Length {len(stream_data)} >>\nstream\n"
            ).encode("latin1") + stream_data + b"\nendstream"
            new_object(c_num, content_dict)

        # Cross Reference Table
        xref_offset = len(buf)
        total_objs = next_obj
        buf.extend(f"xref\n0 {total_objs}\n".encode("latin1"))
        buf.extend(b"0000000000 65535 f \n")
        for i in range(1, total_objs):
            off = offsets[i]
            buf.extend(f"{off:010d} 00000 n \n".encode("latin1"))

        trailer = (
            f"trailer\n"
            f"<< /Size {total_objs}\n"
            f"   /Root 1 0 R\n"
            f">>\n"
            f"startxref\n"
            f"{xref_offset}\n"
            f"%%EOF\n"
        ).encode("latin1")
        buf.extend(trailer)

        with open(self.filename, "wb") as f:
            f.write(buf)
        print(f"Generated PDF: {self.filename} ({len(buf)} bytes, {len(self.pages)} pages)")


def generate_project_guide(live_url="https://protoboot.up.railway.app/", 
                           github_url="https://github.com/ayu37071/Application-Layer",
                           output_pdf="Application_Layer_Visualizer_Guide.pdf"):
    pdf = PDFBuilder(filename=output_pdf)

    # Color Palette: Modern tech aesthetic
    COLOR_PRIMARY = (0.06, 0.09, 0.16)      # slate 900 #0f172a
    COLOR_ACCENT = (0.14, 0.38, 0.92)       # royal blue #2563eb
    COLOR_ACCENT_BG = (0.93, 0.96, 1.0)     # light blue tint
    COLOR_EMERALD = (0.05, 0.60, 0.36)      # vibrant green
    COLOR_EMERALD_BG = (0.91, 0.98, 0.94)   # light green tint
    COLOR_DARK = (0.12, 0.15, 0.20)         # dark body text
    COLOR_MUTED = (0.40, 0.44, 0.52)        # gray text
    COLOR_LIGHT_BG = (0.96, 0.97, 0.99)     # light gray container
    COLOR_BORDER = (0.85, 0.88, 0.92)       # subtle gray border
    COLOR_CODE_BG = (0.09, 0.12, 0.17)      # terminal dark box
    COLOR_CODE_TXT = (0.92, 0.95, 0.98)     # terminal text
    COLOR_WHITE = (1.0, 1.0, 1.0)

    # =========================================================================
    # PAGE 1: Overview, Clickable Links & Layer 7 Protocol Architecture
    # =========================================================================
    pdf.new_page()
    
    # Header Banner
    pdf.rect(0, 735, 595.28, 107, fill_rgb=COLOR_PRIMARY)
    pdf.rect(0, 731, 595.28, 4, fill_rgb=COLOR_ACCENT)
    
    pdf.draw_text(36, 804, "Application Layer Activity & Protocol Visualizer", font="F2", size=17.5, rgb=COLOR_WHITE)
    pdf.draw_text(36, 785, "Interactive Educational Web Platform | Computer Networks (Layer 7 Mechanics)", font="F1", size=9.5, rgb=(0.78, 0.84, 0.92))
    pdf.draw_text(36, 768, "RFC-Accurate Simulation: DNS (1035) | HTTP/1.1 (9112) | SMTP (5321) | HLS (8216)", font="F5", size=8.5, rgb=(0.60, 0.70, 0.84))
    pdf.draw_text(36, 750, "Submission Manual, Setup Guide, and Technical Architecture Defense", font="F2", size=8.5, rgb=(0.35, 0.75, 1.0))

    # SECTION 1: Direct Clickable Links Box (Hero Banner)
    pdf.rounded_rect(36, 615, 523, 104, r=6, fill_rgb=(0.98, 0.99, 1.0), stroke_rgb=COLOR_ACCENT, stroke_width=1.5)
    pdf.draw_text(50, 698, "QUICK ACCESS PROJECT LINKS (CLICKABLE)", font="F2", size=10.5, rgb=COLOR_ACCENT)
    pdf.draw_text(50, 684, "Click either box below to immediately open the online deployment or explore the GitHub repository:", font="F1", size=8.5, rgb=COLOR_MUTED)

    # 1. Live Website Link Card (Clickable)
    pdf.rounded_rect(50, 626, 242, 48, r=4, fill_rgb=COLOR_EMERALD_BG, stroke_rgb=COLOR_EMERALD, stroke_width=1.2)
    pdf.draw_text(60, 658, "ONLINE LIVE WEB APPLICATION:", font="F2", size=8, rgb=COLOR_EMERALD)
    pdf.draw_text(60, 644, live_url, font="F4", size=8, rgb=(0.04, 0.45, 0.28))
    pdf.draw_text(60, 633, "[ CLICK TO OPEN LIVE DEPLOYMENT ]", font="F2", size=7.5, rgb=COLOR_EMERALD)
    pdf.add_link((50, 626, 292, 674), live_url)

    # 2. GitHub Repository Link Card (Clickable)
    pdf.rounded_rect(302, 626, 257, 48, r=4, fill_rgb=COLOR_ACCENT_BG, stroke_rgb=COLOR_ACCENT, stroke_width=1.2)
    pdf.draw_text(312, 658, "GITHUB SOURCE CODE REPOSITORY:", font="F2", size=8, rgb=COLOR_ACCENT)
    pdf.draw_text(312, 644, github_url, font="F4", size=7.5, rgb=(0.10, 0.28, 0.70))
    pdf.draw_text(312, 633, "[ CLICK TO OPEN GITHUB REPOSITORY ]", font="F2", size=7.5, rgb=COLOR_ACCENT)
    pdf.add_link((302, 626, 559, 674), github_url)

    # SECTION 2: Architecture & System Overview
    pdf.draw_text(36, 592, "1. System Overview & Decoupled Architecture", font="F2", size=12, rgb=COLOR_PRIMARY)
    pdf.line(36, 586, 559, 586, stroke_rgb=COLOR_BORDER, stroke_width=1)

    desc_lines = [
        "The Application Layer Activity & Protocol Visualizer is an interactive educational tool designed for Computer Networks",
        "courses. It visually bridges high-level user actions with underlying RFC-compliant wire protocols in real-time.",
        "To provide maximum pedagogical clarity without raw packet fragmentation, the application utilizes a dual-panel layout:"
    ]
    cur_y = 572
    for line in desc_lines:
        pdf.draw_text(36, cur_y, line, font="F1", size=8.5, rgb=COLOR_DARK)
        cur_y -= 12

    # Two panel explanation boxes
    pdf.rounded_rect(36, 460, 254, 78, r=4, fill_rgb=COLOR_LIGHT_BG, stroke_rgb=COLOR_BORDER, stroke_width=1)
    pdf.draw_text(46, 524, "LEFT PANEL: User Activity Client", font="F2", size=9, rgb=COLOR_PRIMARY)
    pdf.draw_text(46, 510, "• Web Browsing: Enter URL, click Visit, load page", font="F1", size=8, rgb=COLOR_DARK)
    pdf.draw_text(46, 497, "• Email Dispatch: Compose sender, recipient, subject", font="F1", size=8, rgb=COLOR_DARK)
    pdf.draw_text(46, 484, "• Video Streaming: Multi-bitrate player & playback", font="F1", size=8, rgb=COLOR_DARK)
    pdf.draw_text(46, 471, "• Activity Log: Chronological history of user triggers", font="F1", size=8, rgb=COLOR_DARK)

    pdf.rounded_rect(304, 460, 255, 78, r=4, fill_rgb=COLOR_LIGHT_BG, stroke_rgb=COLOR_BORDER, stroke_width=1)
    pdf.draw_text(314, 524, "RIGHT PANEL: Protocol Inspection & State", font="F2", size=9, rgb=COLOR_PRIMARY)
    pdf.draw_text(314, 510, "• Animated Flow: Visual Client <-> Server packet paths", font="F1", size=8, rgb=COLOR_DARK)
    pdf.draw_text(314, 497, "• Wire ASCII Data: Authentic RFC grammar & headers", font="F1", size=8, rgb=COLOR_DARK)
    pdf.draw_text(314, 484, "• Interactive Controls: Pause, Resume, Step, Replay", font="F1", size=8, rgb=COLOR_DARK)
    pdf.draw_text(314, 471, "• Stepper Bar: Interactive direct-jump sequence nodes", font="F1", size=8, rgb=COLOR_DARK)

    # SECTION 3: Supported Protocols
    pdf.draw_text(36, 436, "2. Supported Application Layer Protocols (RFC Standards)", font="F2", size=12, rgb=COLOR_PRIMARY)
    pdf.line(36, 430, 559, 430, stroke_rgb=COLOR_BORDER, stroke_width=1)

    flows = [
        ("Web Browsing Exchange", "DNS (RFC 1035) + HTTP/1.1 (RFC 9112)", [
            "Step 1 (DNS Query, UDP :53): Client queries local resolver for IPv4 A-record with Recursion Desired (0x0100).",
            "Step 2 (DNS Response): DNS resolver responds with resolved IP address, TTL cache duration (300s), and flags.",
            "Step 3 (HTTP GET, TCP :80): RFC 9112 GET request with Host, User-Agent, Accept, and Connection: keep-alive.",
            "Step 4 (HTTP 200 OK): Server returns status code, response headers (Content-Type, Content-Length), and HTML body."
        ]),
        ("Electronic Mail Dispatch", "SMTP Protocol (RFC 5321)", [
            "Full 13-step client-server dialog over TCP port 25 with complete MTA state machine validation.",
            "Handshake & Greeting: 220 Service Ready -> EHLO client.fqdn -> 250 ESMTP extensions (PIPELINING, SIZE).",
            "Envelope Negotiation: MAIL FROM:<sender> -> 250 OK -> RCPT TO:<recipient> -> 250 OK.",
            "Data & Delivery: DATA -> 354 Start Input -> MIME Headers + Body -> <CRLF>.<CRLF> -> 250 Queued -> QUIT -> 221 Bye."
        ]),
        ("Adaptive Video Streaming", "HTTP Live Streaming (RFC 8216 / Apple HLS)", [
            "Demonstrates media transmission over ubiquitous HTTP web infrastructure rather than raw UDP/RTSP streams.",
            "DNS lookup for CDN hostname -> Fetches Master Playlist (master.m3u8) listing available bitrate variants.",
            "Fetches Media Variant Playlist (720p/playlist.m3u8) containing 4-second MPEG-TS chunks (segment_1042.ts).",
            "Progressive HTTP GET requests download transport stream segments while dynamically tracking player buffer health."
        ])
    ]

    cur_y = 414
    for title, badge, points in flows:
        pdf.rounded_rect(36, cur_y - 64, 523, 72, r=4, fill_rgb=COLOR_LIGHT_BG, stroke_rgb=COLOR_BORDER, stroke_width=0.8)
        pdf.draw_text(46, cur_y - 4, title, font="F2", size=9, rgb=COLOR_PRIMARY)
        pdf.draw_text(370, cur_y - 4, badge, font="F5", size=7.5, rgb=COLOR_ACCENT)
        pt_y = cur_y - 18
        for pt in points:
            pdf.draw_text(46, pt_y, pt, font="F1", size=7.5, rgb=COLOR_DARK)
            pt_y -= 11.5
        cur_y -= 80

    # SECTION 4: Architecture Components Table
    pdf.draw_text(36, 156, "3. System Architecture & Component Mapping", font="F2", size=10, rgb=COLOR_PRIMARY)
    pdf.line(36, 150, 559, 150, stroke_rgb=COLOR_BORDER, stroke_width=1)

    table_y = 138
    # Table header
    pdf.rect(36, table_y - 4, 523, 16, fill_rgb=COLOR_PRIMARY)
    pdf.draw_text(44, table_y, "MODULE", font="F2", size=7.5, rgb=COLOR_WHITE)
    pdf.draw_text(130, table_y, "ROLE & RESPONSIBILITY", font="F2", size=7.5, rgb=COLOR_WHITE)
    pdf.draw_text(360, table_y, "TECHNOLOGY / STANDARD", font="F2", size=7.5, rgb=COLOR_WHITE)
    pdf.draw_text(480, table_y, "STATUS", font="F2", size=7.5, rgb=COLOR_WHITE)

    components = [
        ("app/main.py", "FastAPI router, static file mounting, and WebSocket lifecycle hosting", "FastAPI / Uvicorn ASGI", "[OK] Active"),
        ("app/websocket_manager.py", "Connection sessions, timer ticker, step scrubber, and client sync", "Python AsyncIO / WebSockets", "[OK] Active"),
        ("app/protocol_simulator.py", "Deterministic RFC protocol packet generation & ASCII wire formatter", "Pydantic Schemas / RFC Spec", "[OK] Active"),
        ("app/static/app.js", "Reactive UI rendering, directional CSS animations, audio/state events", "Vanilla ES6 JavaScript", "[OK] Active")
    ]
    cur_y = table_y - 17
    for mod, role, tech, stat in components:
        pdf.rect(36, cur_y - 3, 523, 14, fill_rgb=COLOR_LIGHT_BG if ((table_y - cur_y) % 2 == 0) else COLOR_WHITE)
        pdf.draw_text(44, cur_y, mod, font="F4", size=7.2, rgb=COLOR_PRIMARY)
        pdf.draw_text(130, cur_y, role, font="F1", size=7.2, rgb=COLOR_DARK)
        pdf.draw_text(360, cur_y, tech, font="F1", size=7.2, rgb=COLOR_ACCENT)
        pdf.draw_text(480, cur_y, stat, font="F2", size=7.2, rgb=COLOR_EMERALD)
        cur_y -= 14

    # Footer Page 1
    pdf.line(36, 42, 559, 42, stroke_rgb=COLOR_BORDER, stroke_width=0.8)
    pdf.draw_text(36, 30, "Application Layer Activity & Protocol Visualizer — Comprehensive Manual", font="F1", size=8, rgb=COLOR_MUTED)
    pdf.draw_text(500, 30, "Page 1 of 3", font="F2", size=8, rgb=COLOR_MUTED)

    # =========================================================================
    # PAGE 2: System Requirements, Step-by-Step Setup & Verification
    # =========================================================================
    pdf.new_page()

    # Page 2 Header Bar
    pdf.rect(0, 796, 595.28, 46, fill_rgb=COLOR_PRIMARY)
    pdf.draw_text(36, 814, "Application Layer Activity & Protocol Visualizer", font="F2", size=13, rgb=COLOR_WHITE)
    pdf.draw_text(380, 814, "SETUP & TESTING INSTRUCTIONS", font="F2", size=8.5, rgb=(0.4, 0.78, 1.0))

    # SECTION 5: System Prerequisites
    pdf.draw_text(36, 765, "4. System Requirements & Prerequisites", font="F2", size=12, rgb=COLOR_PRIMARY)
    pdf.line(36, 759, 559, 759, stroke_rgb=COLOR_BORDER, stroke_width=1)

    reqs = [
        ("Python Runtime:", "Python 3.10 or higher (Python 3.13 recommended, tested across Linux/macOS/Windows)."),
        ("Package Tooling:", "Standard pip or modern uv package manager (recommended for sub-second virtualenv setup)."),
        ("Operating System:", "macOS (Apple Silicon / Intel), Linux (Ubuntu, Debian, Fedora, Arch), Windows 10/11 (WSL/PowerShell)."),
        ("Web Browser:", "Any modern browser with HTML5 WebSocket support (Chrome, Firefox, Safari, Edge, Brave)."),
        ("Port Allocation:", "TCP Port 8000 available for local ASGI server (or custom port via --port flag).")
    ]
    cur_y = 744
    for lbl, val in reqs:
        pdf.draw_text(46, cur_y, lbl, font="F2", size=8.5, rgb=COLOR_PRIMARY)
        pdf.draw_text(160, cur_y, val, font="F1", size=8.5, rgb=COLOR_DARK)
        cur_y -= 15

    # SECTION 6: Step-by-Step Setup Guide
    pdf.draw_text(36, 658, "5. Step-by-Step Installation & Local Setup", font="F2", size=12, rgb=COLOR_PRIMARY)
    pdf.line(36, 652, 559, 652, stroke_rgb=COLOR_BORDER, stroke_width=1)

    steps = [
        ("Step 1: Clone the GitHub Repository", [
            "# Clone the official project repository from GitHub",
            f"git clone {github_url}.git",
            "cd Application-Layer"
        ]),
        ("Step 2: Create a Dedicated Virtual Environment", [
            "# Option A: Using modern uv (recommended for ultra-fast creation)",
            "uv venv --python 3.13 .venv",
            "# Option B: Using standard Python 3 venv module",
            "python3 -m venv .venv"
        ]),
        ("Step 3: Activate the Virtual Environment", [
            "# On macOS and Linux systems:",
            "source .venv/bin/activate",
            "# On Windows (Command Prompt / PowerShell):",
            ".\\.venv\\Scripts\\activate"
        ]),
        ("Step 4: Install Required Python Dependencies", [
            "# Install production runtime and testing libraries",
            "pip install -r requirements.txt",
            "# (Packages: fastapi, uvicorn[standard], pydantic, jinja2, websockets, pytest, httpx)"
        ])
    ]

    cur_y = 636
    for step_title, code_lines in steps:
        pdf.draw_text(36, cur_y, step_title, font="F2", size=9.2, rgb=COLOR_ACCENT)
        cur_y -= 12
        
        box_h = len(code_lines) * 12.5 + 8
        pdf.rounded_rect(36, cur_y - box_h + 8, 523, box_h, r=3, fill_rgb=COLOR_CODE_BG)
        box_text_y = cur_y - 2
        for line in code_lines:
            rgb_val = (0.55, 0.65, 0.75) if line.startswith("#") else COLOR_CODE_TXT
            font_choice = "F5" if line.startswith("#") else "F3"
            pdf.draw_text(48, box_text_y, line, font=font_choice, size=8, rgb=rgb_val)
            box_text_y -= 12.5
        cur_y = cur_y - box_h - 9

    # SECTION 7: Automated Verification & Test Suite
    pdf.draw_text(36, cur_y + 4, "6. Automated Verification & Quality Assurance", font="F2", size=12, rgb=COLOR_PRIMARY)
    pdf.line(36, cur_y - 2, 559, cur_y - 2, stroke_rgb=COLOR_BORDER, stroke_width=1)
    cur_y -= 16

    pdf.draw_text(36, cur_y, "Run the automated Pytest test suite to verify protocol generator correctness, schemas, and endpoints:", font="F1", size=8.5, rgb=COLOR_DARK)
    cur_y -= 14

    test_commands = [
        "# Execute all automated test suites with verbose output",
        "pytest tests/test_protocol_simulator.py -v"
    ]
    box_h = len(test_commands) * 13 + 8
    pdf.rounded_rect(36, cur_y - box_h + 8, 523, box_h, r=3, fill_rgb=COLOR_CODE_BG)
    box_text_y = cur_y - 2
    for line in test_commands:
        rgb_val = (0.55, 0.65, 0.75) if line.startswith("#") else (0.2, 0.9, 0.6)
        pdf.draw_text(48, box_text_y, line, font="F3", size=8, rgb=rgb_val)
        box_text_y -= 13
    cur_y = cur_y - box_h - 12

    test_details = [
        ("[OK] DNS Resolution Test", "Verifies A-record packaging, 300s TTL header validation, and recursive query IDs."),
        ("[OK] HTTP/1.1 Transaction", "Confirms RFC 9112 header syntax, host headers, content length, and HTML entity payload."),
        ("[OK] SMTP State Machine", "Validates the full 13-stage RFC 5321 conversation, greeting codes, and QUIT termination."),
        ("[OK] HLS Video Manifests", "Validates master manifest parsing (#EXT-X-STREAM-INF) and chunk index sequencing."),
        ("[OK] WebSocket Lifecycle", "Ensures dynamic client connection handling, message dispatching, and disconnection safety.")
    ]

    for title, exp in test_details:
        pdf.draw_text(46, cur_y, title, font="F2", size=8, rgb=COLOR_EMERALD)
        pdf.draw_text(180, cur_y, exp, font="F1", size=8, rgb=COLOR_DARK)
        cur_y -= 13

    # Extra Tech Stack Badge Box to fill page 2 elegantly
    pdf.rounded_rect(36, 68, 523, 44, r=4, fill_rgb=COLOR_LIGHT_BG, stroke_rgb=COLOR_BORDER, stroke_width=0.8)
    pdf.draw_text(46, 96, "DEPENDENCY VERIFICATION:", font="F2", size=8, rgb=COLOR_PRIMARY)
    pdf.draw_text(46, 82, "FastAPI >= 0.115.0  |  Uvicorn >= 0.30.0  |  Pydantic >= 2.8.0  |  Jinja2 >= 3.1.4  |  WebSockets >= 12.0  |  Pytest >= 8.0.0", font="F3", size=7.2, rgb=COLOR_ACCENT)

    # Footer Page 2
    pdf.line(36, 42, 559, 42, stroke_rgb=COLOR_BORDER, stroke_width=0.8)
    pdf.draw_text(36, 30, "Application Layer Activity & Protocol Visualizer — Comprehensive Manual", font="F1", size=8, rgb=COLOR_MUTED)
    pdf.draw_text(500, 30, "Page 2 of 3", font="F2", size=8, rgb=COLOR_MUTED)

    # =========================================================================
    # PAGE 3: Execution, Controls, Cloud Deployment & Viva Defense
    # =========================================================================
    pdf.new_page()

    # Page 3 Header Bar
    pdf.rect(0, 796, 595.28, 46, fill_rgb=COLOR_PRIMARY)
    pdf.draw_text(36, 814, "Application Layer Activity & Protocol Visualizer", font="F2", size=13, rgb=COLOR_WHITE)
    pdf.draw_text(370, 814, "EXECUTION & CLOUD DEPLOYMENT", font="F2", size=8.5, rgb=(0.4, 0.78, 1.0))

    # SECTION 8: Execution Instructions
    pdf.draw_text(36, 765, "7. How to Execute & Access the Web Dashboard", font="F2", size=12, rgb=COLOR_PRIMARY)
    pdf.line(36, 759, 559, 759, stroke_rgb=COLOR_BORDER, stroke_width=1)

    pdf.draw_text(36, 745, "Launch the local ASGI production/development server using Uvicorn:", font="F1", size=8.5, rgb=COLOR_DARK)

    exec_commands = [
        "# Start local server with hot-reload enabled (binds to 127.0.0.1:8000)",
        "uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
    ]
    box_h = len(exec_commands) * 13 + 8
    pdf.rounded_rect(36, 715, 523, box_h, r=3, fill_rgb=COLOR_CODE_BG)
    pdf.draw_text(48, 730, exec_commands[0], font="F5", size=8, rgb=(0.55, 0.65, 0.75))
    pdf.draw_text(48, 718, exec_commands[1], font="F3", size=8.5, rgb=COLOR_WHITE)

    pdf.draw_text(36, 694, "Server Endpoints & URLs:", font="F2", size=9, rgb=COLOR_PRIMARY)
    
    endpoints = [
        ("Web Dashboard UI:", "http://127.0.0.1:8000", "Interactive dual-panel visualization interface"),
        ("Health Check Endpoint:", "http://127.0.0.1:8000/health", "Returns JSON status: {'status': 'ok'}"),
        ("WebSocket Endpoint:", "ws://127.0.0.1:8000/ws", "Bidirectional protocol state synchronization feed")
    ]
    cur_y = 678
    for ep_name, ep_url, ep_desc in endpoints:
        pdf.draw_text(46, cur_y, ep_name, font="F2", size=8, rgb=COLOR_PRIMARY)
        pdf.draw_text(180, cur_y, ep_url, font="F4", size=8, rgb=COLOR_ACCENT)
        pdf.draw_text(330, cur_y, ep_desc, font="F1", size=8, rgb=COLOR_MUTED)
        cur_y -= 14

    # SECTION 9: Interactive Playback & Dashboard Features
    pdf.draw_text(36, 622, "8. Interactive Controls & Dashboard Navigation", font="F2", size=12, rgb=COLOR_PRIMARY)
    pdf.line(36, 616, 559, 616, stroke_rgb=COLOR_BORDER, stroke_width=1)

    controls = [
        ("Pause ( || )", "Freezes protocol transmission progression so students can inspect byte fields and headers at leisure."),
        ("Resume ( > )", "Resumes automated step-by-step transmission ticker based on protocol-defined intervals."),
        ("Step Prev ( < )", "Steps backward one packet in the sequence to compare request/response pairs."),
        ("Step Next ( > )", "Advances exactly one packet forward without auto-advancing, enabling classroom discussion."),
        ("Replay ( << )", "Resets the simulation to Packet #1 and replays the entire exchange from the beginning."),
        ("Direct Scrubber", "Click on any circular step indicator in the timeline header to jump directly to that protocol event.")
    ]
    cur_y = 600
    for name, desc in controls:
        pdf.draw_text(46, cur_y, name, font="F2", size=8, rgb=COLOR_ACCENT)
        pdf.draw_text(140, cur_y, desc, font="F1", size=8, rgb=COLOR_DARK)
        cur_y -= 13.5

    # SECTION 10: Cloud Deployment (Railway / Production)
    pdf.draw_text(36, 506, "9. Cloud Deployment Configuration (Railway / Railpack)", font="F2", size=12, rgb=COLOR_PRIMARY)
    pdf.line(36, 500, 559, 500, stroke_rgb=COLOR_BORDER, stroke_width=1)

    dep_lines = [
        "This project is configured for zero-downtime deployment on Railway using Railpack.",
        "To avoid the 'No start command detected' error, the project includes both a Procfile and root main.py entry point:"
    ]
    cur_y = 486
    for dl in dep_lines:
        pdf.draw_text(36, cur_y, dl, font="F1", size=8.5, rgb=COLOR_DARK)
        cur_y -= 12

    # Method 1 & 2 Cards
    pdf.rounded_rect(36, 395, 254, 72, r=4, fill_rgb=COLOR_LIGHT_BG, stroke_rgb=COLOR_BORDER, stroke_width=1)
    pdf.draw_text(46, 452, "Procfile Configuration (Root)", font="F2", size=8.5, rgb=COLOR_PRIMARY)
    pdf.draw_text(46, 439, "Stored at the repository root:", font="F1", size=7.5, rgb=COLOR_MUTED)
    pdf.draw_text(46, 424, "web: uvicorn app.main:app \\", font="F3", size=7.5, rgb=COLOR_DARK)
    pdf.draw_text(75, 412, "--host 0.0.0.0 --port ${PORT:-8000}", font="F3", size=7.5, rgb=COLOR_DARK)

    pdf.rounded_rect(304, 395, 255, 72, r=4, fill_rgb=COLOR_LIGHT_BG, stroke_rgb=COLOR_BORDER, stroke_width=1)
    pdf.draw_text(314, 452, "Railway Dashboard Setting (Fallback)", font="F2", size=8.5, rgb=COLOR_PRIMARY)
    pdf.draw_text(314, 439, "Under Service Settings -> Deploy:", font="F1", size=7.5, rgb=COLOR_MUTED)
    pdf.draw_text(314, 426, "Set Custom Start Command to:", font="F1", size=7.5, rgb=COLOR_MUTED)
    pdf.draw_text(314, 412, "uvicorn app.main:app --host 0.0.0.0", font="F3", size=7.5, rgb=COLOR_ACCENT)
    pdf.draw_text(314, 402, "                     --port ${PORT:-8000}", font="F3", size=7.5, rgb=COLOR_ACCENT)

    # SECTION 11: Viva & Evaluator Presentation Notes
    pdf.draw_text(36, 368, "10. Student Viva & Project Defense Notes", font="F2", size=12, rgb=COLOR_PRIMARY)
    pdf.line(36, 362, 559, 362, stroke_rgb=COLOR_BORDER, stroke_width=1)

    viva_points = [
        ("Layer 7 Abstraction:", "Lower-layer handshakes (TCP 3-way handshake SYN/ACK, TLS 1.3 key exchange, IP routing) occur transparently below Layer 7. Focusing exclusively on Application Layer guarantees clean inspection of ASCII protocol grammar."),
        ("Deterministic Simulation:", "Port 25 (SMTP) is universally blocked by residential and university networks to curb spam. Deterministic simulation guarantees 100% reliable, zero-latency classroom demonstrations with real RFC fidelity."),
        ("Why HLS uses HTTP:", "HLS uses HTTP over standard TCP/80 or TCP/443 instead of raw UDP (RTSP), allowing video chunks to pass transparently through corporate firewalls, NATs, and exploit standard CDN caching infrastructure.")
    ]
    cur_y = 346
    for title, explanation in viva_points:
        pdf.draw_text(46, cur_y, title, font="F2", size=8, rgb=COLOR_PRIMARY)
        words = explanation.split()
        l1, l2 = "", ""
        for w in words:
            if len(l1 + " " + w) < 92:
                l1 += (" " if l1 else "") + w
            else:
                l2 += (" " if l2 else "") + w
        pdf.draw_text(160, cur_y, l1, font="F1", size=7.8, rgb=COLOR_DARK)
        if l2:
            cur_y -= 10.5
            pdf.draw_text(160, cur_y, l2, font="F1", size=7.8, rgb=COLOR_DARK)
        cur_y -= 14

    # Bottom Callout Box for Clickable Links reminder on Page 3
    pdf.rounded_rect(36, 68, 523, 46, r=4, fill_rgb=(0.95, 0.98, 1.0), stroke_rgb=COLOR_ACCENT, stroke_width=1.2)
    pdf.draw_text(50, 97, "ONLINE LIVE DEMO (Clickable):", font="F2", size=8.5, rgb=COLOR_EMERALD)
    pdf.draw_text(220, 97, live_url, font="F4", size=8.5, rgb=(0.04, 0.45, 0.28))
    pdf.add_link((220, 90, 480, 108), live_url)

    pdf.draw_text(50, 81, "GITHUB REPOSITORY (Clickable):", font="F2", size=8.5, rgb=COLOR_ACCENT)
    pdf.draw_text(220, 81, github_url, font="F4", size=8.5, rgb=(0.10, 0.28, 0.70))
    pdf.add_link((220, 73, 510, 92), github_url)

    # Footer Page 3
    pdf.line(36, 42, 559, 42, stroke_rgb=COLOR_BORDER, stroke_width=0.8)
    pdf.draw_text(36, 30, "Application Layer Activity & Protocol Visualizer — Comprehensive Manual", font="F1", size=8, rgb=COLOR_MUTED)
    pdf.draw_text(500, 30, "Page 3 of 3", font="F2", size=8, rgb=COLOR_MUTED)

    pdf.build_pdf()


if __name__ == "__main__":
    live = sys.argv[1] if len(sys.argv) > 1 else "https://protoboot.up.railway.app/"
    github = sys.argv[2] if len(sys.argv) > 2 else "https://github.com/ayu37071/Application-Layer"
    out = sys.argv[3] if len(sys.argv) > 3 else "Application_Layer_Visualizer_Guide.pdf"
    generate_project_guide(live_url=live, github_url=github, output_pdf=out)
