"""
Deterministic, RFC-Accurate Protocol Simulator for Application Layer Visualizer.
Generates realistic wire-accurate protocol exchanges for:
1. Browsing (DNS Resolution + HTTP/1.1 Request/Response)
2. Mail (SMTP Transaction State Machine - RFC 5321)
3. Streaming (Adaptive Bitrate Streaming - HLS Master, Media Playlist, and Segments)
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.protocol_models import (
    ActivityType,
    Direction,
    HighlightField,
    ProtocolStep,
    ProtocolType,
    StepSummary,
)


def _hash_to_ip(domain: str) -> str:
    """Deterministically produce a realistic public IPv4 from a domain name."""
    digest = hashlib.md5(domain.encode("utf-8")).hexdigest()
    octet1 = 93 + (int(digest[0:2], 16) % 40)
    octet2 = 184 + (int(digest[2:4], 16) % 30)
    octet3 = 10 + (int(digest[4:6], 16) % 150)
    octet4 = 2 + (int(digest[6:8], 16) % 240)
    return f"{octet1}.{octet2}.{octet3}.{octet4}"


def generate_browsing_steps(url_str: str) -> List[ProtocolStep]:
    """
    Generates the complete 4-step Browsing exchange:
    1. DNS Query (UDP 53)
    2. DNS Response (UDP 53)
    3. HTTP/1.1 GET Request (TCP 80)
    4. HTTP/1.1 200 OK Response (TCP 80)
    """
    if not url_str:
        url_str = "http://gaia.cs.umass.edu/kurose_ross/interactive/"

    if not (url_str.startswith("http://") or url_str.startswith("https://")):
        url_str = "http://" + url_str

    parsed = urlparse(url_str)
    hostname = parsed.hostname or "example.edu"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += f"?{parsed.query}"

    server_ip = _hash_to_ip(hostname)
    client_ip = "192.168.1.105"
    dns_server_ip = "8.8.8.8"
    tx_id_hex = "0x" + hashlib.md5(hostname.encode()).hexdigest()[:4]

    steps: List[ProtocolStep] = []
    total = 4

    # --- Step 1: DNS Query ---
    dns_query_raw = (
        f"Domain Name System (query)\n"
        f"Transaction ID: {tx_id_hex}\n"
        f"Flags: 0x0100 Standard query\n"
        f"    0... .... .... .... = Response: Message is a query\n"
        f"    .000 0... .... .... = Opcode: Standard query (0)\n"
        f"    .... ..0. .... .... = Truncated: Message is not truncated\n"
        f"    .... ...1 .... .... = Recursion desired: Do query recursively\n"
        f"    .... .... .0.. .... = Z: reserved (0)\n"
        f"    .... .... ..0. .... = Non-authenticated data: Unacceptable\n"
        f"Questions: 1\n"
        f"Answer RRs: 0\n"
        f"Authority RRs: 0\n"
        f"Additional RRs: 0\n"
        f"Queries:\n"
        f"    {hostname}: type A, class IN\n"
        f"        Name: {hostname}\n"
        f"        Type: A (Host Address) (1)\n"
        f"        Class: IN (0x0001)"
    )
    steps.append(
        ProtocolStep(
            step_id=1,
            total_steps=total,
            protocol=ProtocolType.DNS,
            direction=Direction.CLIENT_TO_SERVER,
            sender=f"Client ({client_ip}:54120)",
            receiver=f"DNS Server ({dns_server_ip}:53)",
            summary=f"DNS Standard Query: A {hostname}",
            raw_message=dns_query_raw,
            highlighted_fields=[
                HighlightField(name="Transaction ID", value=tx_id_hex, description="16-bit identifier matching query to response"),
                HighlightField(name="Query Name", value=hostname, description="Target domain to resolve"),
                HighlightField(name="Record Type", value="A (IPv4)", description="Requests standard 32-bit IPv4 address"),
                HighlightField(name="Flags", value="0x0100 (RD)", description="Recursion Desired flag set by client stub resolver"),
            ],
            explanation=(
                f"Before opening a TCP connection to {hostname}, the browser's operating system stub resolver "
                f"sends a UDP query on port 53 to local DNS resolver {dns_server_ip} asking for the IPv4 (A record) address."
            ),
            relative_time_ms=0,
        )
    )

    # --- Step 2: DNS Response ---
    dns_response_raw = (
        f"Domain Name System (response)\n"
        f"Transaction ID: {tx_id_hex}\n"
        f"Flags: 0x8180 Standard query response, No error\n"
        f"    1... .... .... .... = Response: Message is a response\n"
        f"    .000 0... .... .... = Opcode: Standard query (0)\n"
        f"    .... .0.. .... .... = Authoritative: Server is not an authority for domain\n"
        f"    .... ..0. .... .... = Truncated: Message is not truncated\n"
        f"    .... ...1 .... .... = Recursion desired: Do query recursively\n"
        f"    .... .... 1... .... = Recursion available: Server can do recursive queries\n"
        f"    .... .... .... 0000 = Reply code: No error (0)\n"
        f"Questions: 1\n"
        f"Answer RRs: 1\n"
        f"Authority RRs: 0\n"
        f"Additional RRs: 0\n"
        f"Answers:\n"
        f"    {hostname}: type A, class IN, TTL 300, addr {server_ip}\n"
        f"        Name: {hostname}\n"
        f"        Type: A (Host Address) (1)\n"
        f"        Class: IN (0x0001)\n"
        f"        Time to live: 300 (5 minutes)\n"
        f"        Data length: 4\n"
        f"        Address: {server_ip}"
    )
    steps.append(
        ProtocolStep(
            step_id=2,
            total_steps=total,
            protocol=ProtocolType.DNS,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"DNS Server ({dns_server_ip}:53)",
            receiver=f"Client ({client_ip}:54120)",
            summary=f"DNS Response: {hostname} -> {server_ip}",
            raw_message=dns_response_raw,
            highlighted_fields=[
                HighlightField(name="Transaction ID", value=tx_id_hex, description="Matches query ID 0x" + tx_id_hex[2:]),
                HighlightField(name="Resolved IP", value=server_ip, description="IPv4 host address of web server"),
                HighlightField(name="TTL", value="300s (5 min)", description="Time to live cache validity in seconds"),
                HighlightField(name="RCODE", value="0 (NoError)", description="DNS response status code"),
            ],
            explanation=(
                f"The recursive resolver responds with answer {server_ip}. The client caches this mapping for "
                f"300 seconds (TTL) so subsequent requests will not need to re-query DNS."
            ),
            relative_time_ms=38,
        )
    )

    # --- Step 3: HTTP GET Request ---
    http_req_raw = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {hostname}\r\n"
        f"User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36\r\n"
        f"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8\r\n"
        f"Accept-Language: en-US,en;q=0.9\r\n"
        f"Accept-Encoding: gzip, deflate\r\n"
        f"Connection: keep-alive\r\n"
        f"Upgrade-Insecure-Requests: 1\r\n"
        f"\r\n"
    )
    steps.append(
        ProtocolStep(
            step_id=3,
            total_steps=total,
            protocol=ProtocolType.HTTP,
            direction=Direction.CLIENT_TO_SERVER,
            sender=f"Client ({client_ip}:51200)",
            receiver=f"Web Server ({server_ip}:{port})",
            summary=f"HTTP GET {path} HTTP/1.1",
            raw_message=http_req_raw,
            highlighted_fields=[
                HighlightField(name="Method", value="GET", description="HTTP request verb to retrieve resource"),
                HighlightField(name="Path", value=path, description="Target resource URI on the host"),
                HighlightField(name="Host", value=hostname, description="Mandatory HTTP/1.1 host header for virtual hosting"),
                HighlightField(name="Connection", value="keep-alive", description="Requests persistent TCP connection"),
            ],
            explanation=(
                f"After the underlying TCP 3-way handshake completes, the browser sends an RFC 9112 HTTP/1.1 GET request "
                f"specifying the Host header and client capabilities."
            ),
            relative_time_ms=95,
        )
    )

    # --- Step 4: HTTP 200 OK Response ---
    html_body = (
        f"<!DOCTYPE html>\n"
        f"<html lang=\"en\">\n"
        f"<head>\n"
        f"  <meta charset=\"UTF-8\">\n"
        f"  <title>Welcome to {hostname}</title>\n"
        f"</head>\n"
        f"<body>\n"
        f"  <header><h1>{hostname}</h1></header>\n"
        f"  <main>\n"
        f"    <p>Status: 200 OK — Resource delivered successfully.</p>\n"
        f"    <p>Path requested: <code>{path}</code></p>\n"
        f"  </main>\n"
        f"</body>\n"
        f"</html>\n"
    )
    content_len = len(html_body.encode("utf-8"))
    now_http = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    http_resp_raw = (
        f"HTTP/1.1 200 OK\r\n"
        f"Date: {now_http}\r\n"
        f"Server: Apache/2.4.58 (Ubuntu)\r\n"
        f"Last-Modified: Mon, 14 Sep 2026 10:00:00 GMT\r\n"
        f"ETag: \"2d7f8-62024b31-89a0\"\r\n"
        f"Accept-Ranges: bytes\r\n"
        f"Content-Length: {content_len}\r\n"
        f"Content-Type: text/html; charset=UTF-8\r\n"
        f"Connection: keep-alive\r\n"
        f"\r\n"
        f"{html_body}"
    )
    steps.append(
        ProtocolStep(
            step_id=4,
            total_steps=total,
            protocol=ProtocolType.HTTP,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"Web Server ({server_ip}:{port})",
            receiver=f"Client ({client_ip}:51200)",
            summary="HTTP/1.1 200 OK (text/html)",
            raw_message=http_resp_raw,
            highlighted_fields=[
                HighlightField(name="Status Code", value="200 OK", description="Standard HTTP success code"),
                HighlightField(name="Content-Type", value="text/html; charset=UTF-8", description="MIME type indicating HTML markup"),
                HighlightField(name="Content-Length", value=f"{content_len} bytes", description="Exact byte size of response body"),
                HighlightField(name="Server", value="Apache/2.4.58 (Ubuntu)", description="Web server software banner"),
            ],
            explanation=(
                f"The web server locates {path}, builds response headers including Content-Type and Content-Length, "
                f"and transmits the HTML entity body back over the TCP connection."
            ),
            relative_time_ms=160,
        )
    )

    return steps


def generate_mail_steps(params: Dict[str, Any]) -> List[ProtocolStep]:
    """
    Generates the complete 13-step SMTP transaction (RFC 5321):
    1. Server 220 Greeting
    2. Client EHLO
    3. Server 250 with capabilities
    4. Client MAIL FROM
    5. Server 250 Sender OK
    6. Client RCPT TO
    7. Server 250 Recipient OK
    8. Client DATA
    9. Server 354 Start mail input
    10. Client MIME Headers & Message Body followed by <CRLF>.<CRLF>
    11. Server 250 Queued
    12. Client QUIT
    13. Server 221 Bye
    """
    to_email = params.get("to") or "professor@university.edu"
    from_email = params.get("from") or "student@course.edu"
    subject = params.get("subject") or "Course Project Milestone"
    body_text = params.get("body") or "Dear Professor,\n\nPlease find our Application Layer project submission attached.\n\nBest regards,\nStudent"

    # Extract target mail domain
    recipient_domain = to_email.split("@")[-1] if "@" in to_email else "university.edu"
    mail_server_host = f"mail.{recipient_domain}"
    mail_server_ip = _hash_to_ip(mail_server_host)
    client_ip = "192.168.1.105"
    queue_id = hashlib.md5(f"{to_email}{subject}".encode()).hexdigest()[:8].upper()

    total = 13
    steps: List[ProtocolStep] = []

    # Step 1: Server 220 Greeting
    steps.append(
        ProtocolStep(
            step_id=1,
            total_steps=total,
            protocol=ProtocolType.SMTP,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"Mail Server ({mail_server_ip}:25)",
            receiver=f"Client ({client_ip}:49810)",
            summary="220 Service ready greeting banner",
            raw_message=f"220 {mail_server_host} ESMTP Postfix (Ubuntu/24.04)",
            highlighted_fields=[
                HighlightField(name="Status Code", value="220", description="SMTP Service Ready reply code"),
                HighlightField(name="Domain", value=mail_server_host, description="Fully qualified domain of receiving MTA"),
                HighlightField(name="ESMTP", value="Enabled", description="Indicates Extended SMTP support"),
            ],
            explanation=(
                f"Upon accepting the TCP connection on port 25, the destination Mail Transfer Agent (MTA) "
                f"sends a 220 greeting banner announcing that it is ready to receive SMTP commands."
            ),
            relative_time_ms=0,
        )
    )

    # Step 2: Client EHLO
    client_fqdn = "workstation-01.course.edu"
    steps.append(
        ProtocolStep(
            step_id=2,
            total_steps=total,
            protocol=ProtocolType.SMTP,
            direction=Direction.CLIENT_TO_SERVER,
            sender=f"Client ({client_ip}:49810)",
            receiver=f"Mail Server ({mail_server_ip}:25)",
            summary=f"EHLO {client_fqdn}",
            raw_message=f"EHLO {client_fqdn}",
            highlighted_fields=[
                HighlightField(name="Command", value="EHLO", description="Extended HELLO command (RFC 5321)"),
                HighlightField(name="Client FQDN", value=client_fqdn, description="Client fully qualified domain name"),
            ],
            explanation=(
                f"The client identifies itself using the EHLO command. This initializes the SMTP session "
                f"and asks the server to advertise its supported extensions."
            ),
            relative_time_ms=45,
        )
    )

    # Step 3: Server 250 EHLO Response with extensions
    ehlo_resp_raw = (
        f"250-{mail_server_host}\r\n"
        f"250-PIPELINING\r\n"
        f"250-SIZE 20480000\r\n"
        f"250-VRFY\r\n"
        f"250-ETRN\r\n"
        f"250-8BITMIME\r\n"
        f"250-ENHANCEDSTATUSCODES\r\n"
        f"250-CHUNKING\r\n"
        f"250 SMTPUTF8"
    )
    steps.append(
        ProtocolStep(
            step_id=3,
            total_steps=total,
            protocol=ProtocolType.SMTP,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"Mail Server ({mail_server_ip}:25)",
            receiver=f"Client ({client_ip}:49810)",
            summary="250 ESMTP extensions list",
            raw_message=ehlo_resp_raw,
            highlighted_fields=[
                HighlightField(name="Status Code", value="250 OK", description="Handshake accepted"),
                HighlightField(name="Max Size", value="20 MB (20480000 bytes)", description="Max acceptable message size"),
                HighlightField(name="Features", value="PIPELINING, 8BITMIME, SMTPUTF8", description="Server supported ESMTP extensions"),
            ],
            explanation=(
                "The server replies with a multi-line 250 response (indicated by hyphens `250-`) detailing its capabilities, "
                "such as maximum message size limit and 8-bit MIME transport."
            ),
            relative_time_ms=90,
        )
    )

    # Step 4: Client MAIL FROM
    mail_from_cmd = f"MAIL FROM:<{from_email}>"
    steps.append(
        ProtocolStep(
            step_id=4,
            total_steps=total,
            protocol=ProtocolType.SMTP,
            direction=Direction.CLIENT_TO_SERVER,
            sender=f"Client ({client_ip}:49810)",
            receiver=f"Mail Server ({mail_server_ip}:25)",
            summary=mail_from_cmd,
            raw_message=mail_from_cmd,
            highlighted_fields=[
                HighlightField(name="Command", value="MAIL FROM", description="Initiates mail transaction"),
                HighlightField(name="Envelope Sender", value=f"<{from_email}>", description="Return path for non-delivery notifications (NDR)"),
            ],
            explanation=(
                f"The client initiates an envelope transaction with MAIL FROM. This tells the server who is sending the message "
                f"and where bounce reports should be routed."
            ),
            relative_time_ms=135,
        )
    )

    # Step 5: Server 250 Sender OK
    steps.append(
        ProtocolStep(
            step_id=5,
            total_steps=total,
            protocol=ProtocolType.SMTP,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"Mail Server ({mail_server_ip}:25)",
            receiver=f"Client ({client_ip}:49810)",
            summary="250 2.1.0 Sender OK",
            raw_message=f"250 2.1.0 Sender <{from_email}> OK",
            highlighted_fields=[
                HighlightField(name="Status Code", value="250", description="Action completed successfully"),
                HighlightField(name="Enhanced Code", value="2.1.0", description="Other or undefined status for address valid"),
            ],
            explanation="The server validates the envelope sender syntax and local policies and confirms it will accept mail from this address.",
            relative_time_ms=180,
        )
    )

    # Step 6: Client RCPT TO
    rcpt_to_cmd = f"RCPT TO:<{to_email}>"
    steps.append(
        ProtocolStep(
            step_id=6,
            total_steps=total,
            protocol=ProtocolType.SMTP,
            direction=Direction.CLIENT_TO_SERVER,
            sender=f"Client ({client_ip}:49810)",
            receiver=f"Mail Server ({mail_server_ip}:25)",
            summary=rcpt_to_cmd,
            raw_message=rcpt_to_cmd,
            highlighted_fields=[
                HighlightField(name="Command", value="RCPT TO", description="Specifies envelope recipient"),
                HighlightField(name="Envelope Recipient", value=f"<{to_email}>", description="Mailbox where email must be delivered"),
            ],
            explanation=(
                f"The client specifies the destination mailbox using RCPT TO. Multiple RCPT commands can be sent "
                f"for multiple recipients before DATA."
            ),
            relative_time_ms=225,
        )
    )

    # Step 7: Server 250 Recipient OK
    steps.append(
        ProtocolStep(
            step_id=7,
            total_steps=total,
            protocol=ProtocolType.SMTP,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"Mail Server ({mail_server_ip}:25)",
            receiver=f"Client ({client_ip}:49810)",
            summary="250 2.1.5 Recipient OK",
            raw_message=f"250 2.1.5 Recipient <{to_email}> OK",
            highlighted_fields=[
                HighlightField(name="Status Code", value="250", description="Recipient address accepted"),
                HighlightField(name="Enhanced Code", value="2.1.5", description="Destination address valid"),
            ],
            explanation="The server verifies that the destination mailbox exists (or is relayable) and accepts the recipient.",
            relative_time_ms=270,
        )
    )

    # Step 8: Client DATA
    steps.append(
        ProtocolStep(
            step_id=8,
            total_steps=total,
            protocol=ProtocolType.SMTP,
            direction=Direction.CLIENT_TO_SERVER,
            sender=f"Client ({client_ip}:49810)",
            receiver=f"Mail Server ({mail_server_ip}:25)",
            summary="DATA",
            raw_message="DATA",
            highlighted_fields=[
                HighlightField(name="Command", value="DATA", description="Requests permission to transfer message content"),
            ],
            explanation="The client issues DATA to switch the protocol state from envelope negotiation to message content transmission.",
            relative_time_ms=315,
        )
    )

    # Step 9: Server 354 Start Mail Input
    steps.append(
        ProtocolStep(
            step_id=9,
            total_steps=total,
            protocol=ProtocolType.SMTP,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"Mail Server ({mail_server_ip}:25)",
            receiver=f"Client ({client_ip}:49810)",
            summary="354 Start mail input; end with <CRLF>.<CRLF>",
            raw_message="354 Start mail input; end with <CRLF>.<CRLF>",
            highlighted_fields=[
                HighlightField(name="Status Code", value="354", description="Intermediate positive response"),
                HighlightField(name="Delimiter", value="<CRLF>.<CRLF>", description="Single period on its own line ends message data"),
            ],
            explanation=(
                "The server issues 354, signaling the client to begin streaming the message body. "
                "Per RFC 5321, message transmission concludes when a line containing only a period (.) is received."
            ),
            relative_time_ms=360,
        )
    )

    # Step 10: Client Message Body & Termination Period
    now_smtp = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    message_id = f"<{datetime.now().strftime('%Y%m%d%H%M%S')}.{queue_id}@{client_fqdn}>"
    mail_payload = (
        f"From: {from_email}\r\n"
        f"To: {to_email}\r\n"
        f"Date: {now_smtp}\r\n"
        f"Subject: {subject}\r\n"
        f"Message-ID: {message_id}\r\n"
        f"MIME-Version: 1.0\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"{body_text}\r\n"
        f"."
    )
    steps.append(
        ProtocolStep(
            step_id=10,
            total_steps=total,
            protocol=ProtocolType.SMTP,
            direction=Direction.CLIENT_TO_SERVER,
            sender=f"Client ({client_ip}:49810)",
            receiver=f"Mail Server ({mail_server_ip}:25)",
            summary=f"MIME Content & Termination '.' ({len(mail_payload)} bytes)",
            raw_message=mail_payload,
            highlighted_fields=[
                HighlightField(name="Subject", value=subject, description="User-facing email subject line header"),
                HighlightField(name="Message-ID", value=message_id, description="Globally unique email message identifier"),
                HighlightField(name="Content-Type", value="text/plain; charset=utf-8", description="MIME content description"),
                HighlightField(name="End Delimiter", value=".", description="Single dot on its own line concludes DATA phase"),
            ],
            explanation=(
                "The client sends the RFC 5322 formatted message (headers, blank line, and body text), "
                "followed by `<CRLF>.<CRLF>` to signal completion."
            ),
            relative_time_ms=410,
        )
    )

    # Step 11: Server 250 Queued
    steps.append(
        ProtocolStep(
            step_id=11,
            total_steps=total,
            protocol=ProtocolType.SMTP,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"Mail Server ({mail_server_ip}:25)",
            receiver=f"Client ({client_ip}:49810)",
            summary=f"250 2.0.0 Ok: queued as {queue_id}",
            raw_message=f"250 2.0.0 Ok: queued as {queue_id}",
            highlighted_fields=[
                HighlightField(name="Status Code", value="250", description="Message accepted and committed to spool"),
                HighlightField(name="Queue ID", value=queue_id, description="Internal MTA spool identifier for tracking"),
            ],
            explanation=(
                f"The server writes the email to its spool directory, confirms persistence with queue ID {queue_id}, "
                f"and prepares for delivery or forwarding."
            ),
            relative_time_ms=470,
        )
    )

    # Step 12: Client QUIT
    steps.append(
        ProtocolStep(
            step_id=12,
            total_steps=total,
            protocol=ProtocolType.SMTP,
            direction=Direction.CLIENT_TO_SERVER,
            sender=f"Client ({client_ip}:49810)",
            receiver=f"Mail Server ({mail_server_ip}:25)",
            summary="QUIT",
            raw_message="QUIT",
            highlighted_fields=[
                HighlightField(name="Command", value="QUIT", description="Requests orderly termination of SMTP session"),
            ],
            explanation="The client terminates the SMTP dialog gracefully using the QUIT command.",
            relative_time_ms=510,
        )
    )

    # Step 13: Server 221 Bye
    steps.append(
        ProtocolStep(
            step_id=13,
            total_steps=total,
            protocol=ProtocolType.SMTP,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"Mail Server ({mail_server_ip}:25)",
            receiver=f"Client ({client_ip}:49810)",
            summary="221 2.0.0 Bye (closing channel)",
            raw_message=f"221 2.0.0 {mail_server_host} Service closing transmission channel",
            highlighted_fields=[
                HighlightField(name="Status Code", value="221", description="Service closing transmission channel"),
            ],
            explanation="The server closes its end of the transmission channel. The underlying TCP connection is subsequently torn down via FIN-ACK.",
            relative_time_ms=550,
        )
    )

    return steps


def generate_streaming_steps(params: Dict[str, Any]) -> List[ProtocolStep]:
    """
    Generates the complete 10-step Adaptive Bitrate Streaming exchange (HLS Paradigm):
    1. DNS Query for Media CDN
    2. DNS Response with CDN IP
    3. HTTP GET Master Playlist (master.m3u8)
    4. HTTP 200 OK Master Playlist with multi-bitrate streams
    5. HTTP GET Media/Variant Playlist (e.g. 720p/playlist.m3u8)
    6. HTTP 200 OK Media Playlist with chunk list
    7. HTTP GET Video Segment 0 (seq0.ts)
    8. HTTP 200 OK Video Segment 0
    9. HTTP GET Video Segment 1 (seq1.ts)
    10. HTTP 200 OK Video Segment 1
    """
    quality = params.get("quality") or "720p"
    qualities_meta = {
        "360p": {"bandwidth": "800000", "resolution": "640x360", "chunk_bytes": 412500},
        "720p": {"bandwidth": "2500000", "resolution": "1280x720", "chunk_bytes": 1284000},
        "1080p": {"bandwidth": "5500000", "resolution": "1920x1080", "chunk_bytes": 2840000},
    }
    current_meta = qualities_meta.get(quality, qualities_meta["720p"])

    cdn_host = "cdn.streamnet.tv"
    cdn_ip = "104.21.45.89"
    client_ip = "192.168.1.105"
    dns_server_ip = "8.8.8.8"
    tx_id_hex = "0x8e21"

    total = 10
    steps: List[ProtocolStep] = []

    # --- Step 1: DNS Query for CDN ---
    dns_query_raw = (
        f"Domain Name System (query)\n"
        f"Transaction ID: {tx_id_hex}\n"
        f"Flags: 0x0100 Standard query (Recursion Desired)\n"
        f"Queries:\n"
        f"    {cdn_host}: type A, class IN"
    )
    steps.append(
        ProtocolStep(
            step_id=1,
            total_steps=total,
            protocol=ProtocolType.DNS,
            direction=Direction.CLIENT_TO_SERVER,
            sender=f"Client ({client_ip}:58912)",
            receiver=f"DNS Server ({dns_server_ip}:53)",
            summary=f"DNS Query: A {cdn_host}",
            raw_message=dns_query_raw,
            highlighted_fields=[
                HighlightField(name="Transaction ID", value=tx_id_hex, description="DNS transaction ID"),
                HighlightField(name="Host", value=cdn_host, description="Content Delivery Network hostname"),
                HighlightField(name="Type", value="A", description="IPv4 address lookup"),
            ],
            explanation=(
                f"Video streaming clients first resolve the Content Delivery Network (CDN) edge server address "
                f"({cdn_host}) via DNS."
            ),
            relative_time_ms=0,
        )
    )

    # --- Step 2: DNS Response ---
    dns_resp_raw = (
        f"Domain Name System (response)\n"
        f"Transaction ID: {tx_id_hex}\n"
        f"Flags: 0x8180 Standard query response, No error\n"
        f"Answers:\n"
        f"    {cdn_host}: type A, class IN, TTL 60, addr {cdn_ip}"
    )
    steps.append(
        ProtocolStep(
            step_id=2,
            total_steps=total,
            protocol=ProtocolType.DNS,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"DNS Server ({dns_server_ip}:53)",
            receiver=f"Client ({client_ip}:58912)",
            summary=f"DNS Response: {cdn_host} -> {cdn_ip}",
            raw_message=dns_resp_raw,
            highlighted_fields=[
                HighlightField(name="Resolved CDN Edge IP", value=cdn_ip, description="Closest Anycast CDN edge node"),
                HighlightField(name="TTL", value="60s", description="Short TTL enables quick CDN load balancing"),
            ],
            explanation=(
                f"DNS returns CDN edge IP {cdn_ip}. CDNs use low TTL values (60s) to dynamically steer users "
                f"to the best geographic server."
            ),
            relative_time_ms=35,
        )
    )

    # --- Step 3: HTTP GET Master Playlist ---
    master_req_raw = (
        f"GET /live/stream/master.m3u8 HTTP/1.1\r\n"
        f"Host: {cdn_host}\r\n"
        f"User-Agent: VideoPlayer/3.2 (CourseVisualizer HLS)\r\n"
        f"Accept: application/vnd.apple.mpegurl, application/x-mpegURL\r\n"
        f"Connection: keep-alive\r\n"
        f"\r\n"
    )
    steps.append(
        ProtocolStep(
            step_id=3,
            total_steps=total,
            protocol=ProtocolType.HTTP,
            direction=Direction.CLIENT_TO_SERVER,
            sender=f"Client ({client_ip}:52100)",
            receiver=f"CDN Edge ({cdn_ip}:80)",
            summary="HTTP GET /live/stream/master.m3u8",
            raw_message=master_req_raw,
            highlighted_fields=[
                HighlightField(name="Method", value="GET", description="HTTP GET request for index manifest"),
                HighlightField(name="Resource", value="master.m3u8", description="Top-level HLS Master Playlist"),
            ],
            explanation=(
                "In HTTP Live Streaming (HLS), playback starts by requesting the master playlist. This manifest lists all "
                "available video resolutions and bitrates available for adaptive bitrate switching."
            ),
            relative_time_ms=80,
        )
    )

    # --- Step 4: HTTP 200 OK Master Playlist ---
    master_manifest = (
        "#EXTM3U\n"
        "#EXT-X-VERSION:3\n"
        "#EXT-X-INDEPENDENT-SEGMENTS\n"
        "#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360,CODECS=\"avc1.4d401e,mp4a.40.2\"\n"
        "360p/playlist.m3u8\n"
        "#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720,CODECS=\"avc1.4d401f,mp4a.40.2\"\n"
        "720p/playlist.m3u8\n"
        "#EXT-X-STREAM-INF:BANDWIDTH=5500000,RESOLUTION=1920x1080,CODECS=\"avc1.640028,mp4a.40.2\"\n"
        "1080p/playlist.m3u8\n"
    )
    master_resp_raw = (
        f"HTTP/1.1 200 OK\r\n"
        f"Server: cloudflare-nginx\r\n"
        f"Content-Type: application/vnd.apple.mpegurl\r\n"
        f"Content-Length: {len(master_manifest.encode())}\r\n"
        f"Cache-Control: public, max-age=60\r\n"
        f"Connection: keep-alive\r\n"
        f"\r\n"
        f"{master_manifest}"
    )
    steps.append(
        ProtocolStep(
            step_id=4,
            total_steps=total,
            protocol=ProtocolType.HTTP,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"CDN Edge ({cdn_ip}:80)",
            receiver=f"Client ({client_ip}:52100)",
            summary="HTTP/1.1 200 OK (Master Playlist with 3 variants)",
            raw_message=master_resp_raw,
            highlighted_fields=[
                HighlightField(name="Content-Type", value="application/vnd.apple.mpegurl", description="M3U8 manifest MIME type"),
                HighlightField(name="Bitrate Variants", value="360p (800kbps), 720p (2.5Mbps), 1080p (5.5Mbps)", description="Adaptive stream profiles"),
            ],
            explanation=(
                "The CDN returns the master playlist. The player inspects its local network throughput and display resolution "
                f"and selects the `{quality}` stream profile."
            ),
            relative_time_ms=130,
        )
    )

    # --- Step 5: HTTP GET Variant Playlist ---
    variant_req_raw = (
        f"GET /live/stream/{quality}/playlist.m3u8 HTTP/1.1\r\n"
        f"Host: {cdn_host}\r\n"
        f"User-Agent: VideoPlayer/3.2 (CourseVisualizer HLS)\r\n"
        f"Accept: application/vnd.apple.mpegurl\r\n"
        f"Connection: keep-alive\r\n"
        f"\r\n"
    )
    steps.append(
        ProtocolStep(
            step_id=5,
            total_steps=total,
            protocol=ProtocolType.HTTP,
            direction=Direction.CLIENT_TO_SERVER,
            sender=f"Client ({client_ip}:52100)",
            receiver=f"CDN Edge ({cdn_ip}:80)",
            summary=f"HTTP GET /live/stream/{quality}/playlist.m3u8",
            raw_message=variant_req_raw,
            highlighted_fields=[
                HighlightField(name="Selected Stream", value=quality, description=f"Chosen resolution ({current_meta['resolution']})"),
                HighlightField(name="Target Playlist", value=f"{quality}/playlist.m3u8", description="Media segment index"),
            ],
            explanation=(
                f"The client requests the specific media playlist for `{quality}`. This manifest contains direct URIs "
                f"for discrete 4-second chunk files."
            ),
            relative_time_ms=180,
        )
    )

    # --- Step 6: HTTP 200 OK Variant Playlist ---
    variant_manifest = (
        "#EXTM3U\n"
        "#EXT-X-VERSION:3\n"
        "#EXT-X-TARGETDURATION:4\n"
        "#EXT-X-MEDIA-SEQUENCE:1042\n"
        "#EXTINF:4.000,\n"
        "segment_1042.ts\n"
        "#EXTINF:4.000,\n"
        "segment_1043.ts\n"
        "#EXTINF:4.000,\n"
        "segment_1044.ts\n"
        "#EXTINF:4.000,\n"
        "segment_1045.ts\n"
    )
    variant_resp_raw = (
        f"HTTP/1.1 200 OK\r\n"
        f"Server: cloudflare-nginx\r\n"
        f"Content-Type: application/vnd.apple.mpegurl\r\n"
        f"Content-Length: {len(variant_manifest.encode())}\r\n"
        f"Cache-Control: no-cache\r\n"
        f"Connection: keep-alive\r\n"
        f"\r\n"
        f"{variant_manifest}"
    )
    steps.append(
        ProtocolStep(
            step_id=6,
            total_steps=total,
            protocol=ProtocolType.HTTP,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"CDN Edge ({cdn_ip}:80)",
            receiver=f"Client ({client_ip}:52100)",
            summary=f"HTTP/1.1 200 OK ({quality} Segment Schedule)",
            raw_message=variant_resp_raw,
            highlighted_fields=[
                HighlightField(name="Chunk Duration", value="4.000 seconds (#EXTINF)", description="Length of each video slice"),
                HighlightField(name="Sequence Start", value="1042", description="Media sequence counter for live synchronization"),
            ],
            explanation=(
                "The CDN sends the list of upcoming 4-second video segments. The client can now begin requesting chunks sequentially "
                "to fill its playback buffer."
            ),
            relative_time_ms=230,
        )
    )

    # --- Step 7: HTTP GET Segment 1042 ---
    seg0_req = (
        f"GET /live/stream/{quality}/segment_1042.ts HTTP/1.1\r\n"
        f"Host: {cdn_host}\r\n"
        f"User-Agent: VideoPlayer/3.2 (CourseVisualizer HLS)\r\n"
        f"Accept: video/mp2t, */*\r\n"
        f"Connection: keep-alive\r\n"
        f"\r\n"
    )
    steps.append(
        ProtocolStep(
            step_id=7,
            total_steps=total,
            protocol=ProtocolType.HTTP,
            direction=Direction.CLIENT_TO_SERVER,
            sender=f"Client ({client_ip}:52100)",
            receiver=f"CDN Edge ({cdn_ip}:80)",
            summary=f"HTTP GET /live/stream/{quality}/segment_1042.ts",
            raw_message=seg0_req,
            highlighted_fields=[
                HighlightField(name="Segment File", value="segment_1042.ts", description="First 4-second MPEG-2 Transport Stream chunk"),
                HighlightField(name="Expected Quality", value=quality, description=f"Bitrate target: {current_meta['bandwidth']} bps"),
            ],
            explanation=(
                "The video player begins downloading the first media chunk (`segment_1042.ts`) over standard HTTP/TCP. "
                "Because streaming uses plain HTTP, it easily traverses standard proxies and firewalls."
            ),
            relative_time_ms=280,
        )
    )

    # --- Step 8: HTTP 200 OK Segment 1042 ---
    chunk_bytes = current_meta["chunk_bytes"]
    seg0_resp = (
        f"HTTP/1.1 200 OK\r\n"
        f"Server: cloudflare-nginx\r\n"
        f"Content-Type: video/mp2t\r\n"
        f"Content-Length: {chunk_bytes}\r\n"
        f"Accept-Ranges: bytes\r\n"
        f"Cache-Control: max-age=86400, public\r\n"
        f"Connection: keep-alive\r\n"
        f"\r\n"
        f"[Binary MPEG-TS Audio/Video Data: {chunk_bytes:,} bytes (~{chunk_bytes // 1024} KB)]\n"
        f"47 40 11 10 00 42 f0 25 00 01 c1 00 00 ff 10 00 11 00 01 ff 00 00 ... [0x47 Sync Byte Stream]"
    )
    steps.append(
        ProtocolStep(
            step_id=8,
            total_steps=total,
            protocol=ProtocolType.HTTP,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"CDN Edge ({cdn_ip}:80)",
            receiver=f"Client ({client_ip}:52100)",
            summary=f"HTTP/1.1 200 OK (segment_1042.ts - {chunk_bytes // 1024} KB)",
            raw_message=seg0_resp,
            highlighted_fields=[
                HighlightField(name="Content-Type", value="video/mp2t", description="MPEG-2 Transport Stream container"),
                HighlightField(name="Chunk Size", value=f"{chunk_bytes:,} bytes", description="Transferred payload volume"),
            ],
            explanation=(
                f"The CDN delivers segment 1042 ({chunk_bytes:,} bytes). The player decodes the H.264 video and AAC audio frames "
                f"and initiates video playback."
            ),
            relative_time_ms=360,
        )
    )

    # --- Step 9: HTTP GET Segment 1043 ---
    seg1_req = (
        f"GET /live/stream/{quality}/segment_1043.ts HTTP/1.1\r\n"
        f"Host: {cdn_host}\r\n"
        f"User-Agent: VideoPlayer/3.2 (CourseVisualizer HLS)\r\n"
        f"Accept: video/mp2t, */*\r\n"
        f"Connection: keep-alive\r\n"
        f"\r\n"
    )
    steps.append(
        ProtocolStep(
            step_id=9,
            total_steps=total,
            protocol=ProtocolType.HTTP,
            direction=Direction.CLIENT_TO_SERVER,
            sender=f"Client ({client_ip}:52100)",
            receiver=f"CDN Edge ({cdn_ip}:80)",
            summary=f"HTTP GET /live/stream/{quality}/segment_1043.ts",
            raw_message=seg1_req,
            highlighted_fields=[
                HighlightField(name="Segment File", value="segment_1043.ts", description="Second 4-second video chunk"),
                HighlightField(name="Buffer Health", value="Pipelined", description="Player fetches next chunk while segment 1 plays"),
            ],
            explanation=(
                "While the first chunk is playing back on screen, the video player pipelined request for `segment_1043.ts` "
                "to maintain buffer safety and prevent video stutter/rebuffering."
            ),
            relative_time_ms=420,
        )
    )

    # --- Step 10: HTTP 200 OK Segment 1043 ---
    seg1_resp = (
        f"HTTP/1.1 200 OK\r\n"
        f"Server: cloudflare-nginx\r\n"
        f"Content-Type: video/mp2t\r\n"
        f"Content-Length: {chunk_bytes + 2400}\r\n"
        f"Accept-Ranges: bytes\r\n"
        f"Cache-Control: max-age=86400, public\r\n"
        f"Connection: keep-alive\r\n"
        f"\r\n"
        f"[Binary MPEG-TS Audio/Video Data: {chunk_bytes + 2400:,} bytes (~{(chunk_bytes + 2400) // 1024} KB)]\n"
        f"47 40 11 10 00 42 f0 25 00 01 c1 00 00 ff 10 00 11 00 01 ff 00 00 ... [0x47 Sync Byte Stream]"
    )
    steps.append(
        ProtocolStep(
            step_id=10,
            total_steps=total,
            protocol=ProtocolType.HTTP,
            direction=Direction.SERVER_TO_CLIENT,
            sender=f"CDN Edge ({cdn_ip}:80)",
            receiver=f"Client ({client_ip}:52100)",
            summary=f"HTTP/1.1 200 OK (segment_1043.ts - {(chunk_bytes + 2400) // 1024} KB)",
            raw_message=seg1_resp,
            highlighted_fields=[
                HighlightField(name="Content-Type", value="video/mp2t", description="MPEG-2 Transport Stream container"),
                HighlightField(name="Stream Status", value="Continuous Playback", description="Seamless playback sustained"),
            ],
            explanation=(
                "The CDN finishes delivering segment 1043. The visualizer demonstrates how modern streaming services "
                "leverage simple HTTP GETs to deliver continuous streaming media."
            ),
            relative_time_ms=500,
        )
    )

    return steps


def generate_steps_for_activity(
    activity_type: ActivityType, params: Optional[Dict[str, Any]] = None
) -> List[ProtocolStep]:
    """Factory function to generate steps for any supported activity."""
    p = params or {}
    if activity_type == ActivityType.BROWSING:
        return generate_browsing_steps(p.get("url", ""))
    elif activity_type == ActivityType.MAIL:
        return generate_mail_steps(p)
    elif activity_type == ActivityType.STREAMING:
        return generate_streaming_steps(p)
    else:
        raise ValueError(f"Unknown activity type: {activity_type}")


def get_step_summaries(steps: List[ProtocolStep]) -> List[StepSummary]:
    """Extract lightweight summary list for the timeline navigation bar."""
    return [
        StepSummary(
            step_id=s.step_id,
            protocol=s.protocol,
            direction=s.direction,
            summary=s.summary,
        )
        for s in steps
    ]
