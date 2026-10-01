"""
Deterministic, RFC-Accurate Transport Layer Simulation Engine.
Implements:
1. TCP 3-Way Handshake (SYN, SYN-ACK, ACK)
2. Exact Sequence and Acknowledgement arithmetic engine (RFC 793, RFC 9293)
3. TCP 10-State Connection Machine
4. Flow Control Advertised Window (Window Size)
5. TCP 4-Way Connection Teardown (FIN, ACK, FIN, ACK)
6. Full mapping between Application Layer activities (Browsing, Mail, Streaming) and TCP/UDP segments
7. Optional educational packet loss and retransmission simulation
"""

from typing import Any, Dict, List, Optional, Tuple
from app.protocol_models import (
    ActivityType,
    Direction,
    ProtocolStep,
    ProtocolType,
    TCPState,
    TransportProtocol,
    TransportSegment,
    TransportStats,
)


class TCPConnectionSimulator:
    """
    Manages deterministic TCP sequence numbers, acknowledgement tracking,
    state transitions, and segment formatting for a full TCP dialog.
    """

    def __init__(
        self,
        client_ip: str = "192.168.1.105",
        server_ip: str = "93.184.216.34",
        client_port: int = 52410,
        server_port: int = 80,
        client_isn: int = 1000,
        server_isn: int = 5000,
        window_size: int = 64240,
    ):
        self.client_ip = client_ip
        self.server_ip = server_ip
        self.client_port = client_port
        self.server_port = server_port

        # Sequence and Acknowledgement counters
        self.client_seq = client_isn
        self.server_seq = server_isn
        self.client_ack = 0
        self.server_ack = 0

        # State tracking
        self.client_state = TCPState.CLOSED.value
        self.server_state = TCPState.LISTEN.value
        self.window_size = window_size

        self.segments: List[TransportSegment] = []
        self._current_time_ms = 0

    def _format_raw_tcp(
        self,
        direction: Direction,
        flags: List[str],
        seq: int,
        ack: int,
        payload_len: int,
        window: int,
    ) -> str:
        """Format an educational ASCII Wireshark-style TCP header dissection."""
        src_port = self.client_port if direction == Direction.CLIENT_TO_SERVER else self.server_port
        dst_port = self.server_port if direction == Direction.CLIENT_TO_SERVER else self.client_port

        flag_bits = []
        flag_str_list = []
        is_syn = "SYN" in flags
        is_ack = "ACK" in flags
        is_psh = "PSH" in flags
        is_fin = "FIN" in flags
        is_rst = "RST" in flags

        flag_str = ", ".join(flags)
        next_seq = seq + (1 if (is_syn or is_fin) else payload_len)

        lines = [
            f"Transmission Control Protocol, Src Port: {src_port}, Dst Port: {dst_port}, Seq: {seq}, Ack: {ack}, Len: {payload_len}",
            f"    Source Port: {src_port}",
            f"    Destination Port: {dst_port}",
            f"    Sequence Number: {seq} (relative sequence)",
            f"    [Next Sequence Number: {next_seq}]",
            f"    Acknowledgment Number: {ack}",
            f"    Header Length: 32 bytes (8)",
            f"    Flags: 0x{len(flags):03x} ({flag_str})",
            f"        ...0 .... .... = Urgent (URG): Not set",
            f"        .... {'1' if is_ack else '0'}... .... = Acknowledgment (ACK): {'Set' if is_ack else 'Not set'}",
            f"        .... .{'1' if is_psh else '0'}.. .... = Push (PSH): {'Set' if is_psh else 'Not set'}",
            f"        .... ..{'1' if is_rst else '0'}. .... = Reset (RST): {'Set' if is_rst else 'Not set'}",
            f"        .... ...{'1' if is_syn else '0'} .... = Syn (SYN): {'Set' if is_syn else 'Not set'}",
            f"        .... .... ...{'1' if is_fin else '0'} = Fin (FIN): {'Set' if is_fin else 'Not set'}",
            f"    Window: {window}",
            f"    Checksum: 0x{abs(hash(f'{seq}{ack}')) % 65535:04x} [verified]",
            f"    [Calculated window size: {window}]",
        ]
        if payload_len > 0:
            lines.append(f"    TCP payload ({payload_len} bytes)")
        return "\n".join(lines)

    def _format_raw_udp(self, direction: Direction, length: int) -> str:
        """Format an educational ASCII UDP header dissection."""
        src_port = self.client_port if direction == Direction.CLIENT_TO_SERVER else self.server_port
        dst_port = self.server_port if direction == Direction.CLIENT_TO_SERVER else self.client_port
        return (
            f"User Datagram Protocol, Src Port: {src_port}, Dst Port: {dst_port}\n"
            f"    Source Port: {src_port}\n"
            f"    Destination Port: {dst_port}\n"
            f"    Length: {length + 8}\n"
            f"    Checksum: 0x{abs(hash(f'{src_port}{dst_port}')) % 65535:04x} [verified]\n"
            f"    [UDP payload ({length} bytes)]"
        )

    def send_client_tcp(
        self,
        flags: List[str],
        payload_len: int = 0,
        app_event_id: Optional[int] = None,
        summary: str = "",
        explanation: str = "",
        time_offset_ms: int = 20,
        retransmission: bool = False,
    ) -> TransportSegment:
        """Client transmits a TCP segment to the server."""
        self._current_time_ms += time_offset_ms
        seq = self.client_seq
        ack = self.client_ack

        # State transition on client transmission
        if "SYN" in flags and "ACK" not in flags:
            self.client_state = TCPState.SYN_SENT.value
            self.server_state = TCPState.SYN_RECEIVED.value
            self.client_seq += 1
            self.server_ack = self.client_seq
        elif "FIN" in flags:
            self.client_state = TCPState.FIN_WAIT_1.value
            self.client_seq += 1
            self.server_ack = self.client_seq
        else:
            if payload_len > 0:
                self.client_seq += payload_len
                self.server_ack = self.client_seq

        raw_str = self._format_raw_tcp(
            Direction.CLIENT_TO_SERVER, flags, seq, ack, payload_len, self.window_size
        )

        segment = TransportSegment(
            id=len(self.segments) + 1,
            total_segments=0,  # Updated after generation
            protocol=TransportProtocol.TCP,
            direction=Direction.CLIENT_TO_SERVER,
            source_ip=self.client_ip,
            destination_ip=self.server_ip,
            source_port=self.client_port,
            destination_port=self.server_port,
            seq=seq,
            ack=ack,
            window=self.window_size,
            flags=flags,
            payload_length=payload_len,
            application_event_id=app_event_id,
            client_state=self.client_state,
            server_state=self.server_state,
            summary=summary or f"TCP [{'+'.join(flags)}] Seq={seq} Ack={ack} Len={payload_len}",
            raw_segment=raw_str,
            explanation=explanation,
            relative_time_ms=self._current_time_ms,
            retransmission=retransmission,
        )
        self.segments.append(segment)
        return segment

    def send_server_tcp(
        self,
        flags: List[str],
        payload_len: int = 0,
        app_event_id: Optional[int] = None,
        summary: str = "",
        explanation: str = "",
        time_offset_ms: int = 20,
        retransmission: bool = False,
    ) -> TransportSegment:
        """Server transmits a TCP segment to the client."""
        self._current_time_ms += time_offset_ms
        seq = self.server_seq
        ack = self.server_ack

        # State transition on server transmission
        if "SYN" in flags and "ACK" in flags:
            self.client_ack = self.server_seq + 1
            self.server_seq += 1
        elif "FIN" in flags:
            if self.server_state == TCPState.CLOSE_WAIT.value:
                self.server_state = TCPState.LAST_ACK.value
            self.client_ack = self.server_seq + 1
            self.server_seq += 1
        else:
            if payload_len > 0:
                self.server_seq += payload_len
                self.client_ack = self.server_seq

        raw_str = self._format_raw_tcp(
            Direction.SERVER_TO_CLIENT, flags, seq, ack, payload_len, self.window_size
        )

        segment = TransportSegment(
            id=len(self.segments) + 1,
            total_segments=0,
            protocol=TransportProtocol.TCP,
            direction=Direction.SERVER_TO_CLIENT,
            source_ip=self.server_ip,
            destination_ip=self.client_ip,
            source_port=self.server_port,
            destination_port=self.client_port,
            seq=seq,
            ack=ack,
            window=self.window_size,
            flags=flags,
            payload_length=payload_len,
            application_event_id=app_event_id,
            client_state=self.client_state,
            server_state=self.server_state,
            summary=summary or f"TCP [{'+'.join(flags)}] Seq={seq} Ack={ack} Len={payload_len}",
            raw_segment=raw_str,
            explanation=explanation,
            relative_time_ms=self._current_time_ms,
            retransmission=retransmission,
        )
        self.segments.append(segment)
        return segment

    def add_udp_datagram(
        self,
        direction: Direction,
        src_port: int,
        dst_port: int,
        payload_len: int,
        app_event_id: Optional[int],
        summary: str,
        explanation: str,
        time_offset_ms: int = 15,
    ) -> TransportSegment:
        """Add a connectionless UDP datagram (e.g. DNS resolution)."""
        self._current_time_ms += time_offset_ms
        src_ip = self.client_ip if direction == Direction.CLIENT_TO_SERVER else self.server_ip
        dst_ip = self.server_ip if direction == Direction.CLIENT_TO_SERVER else self.client_ip

        raw_str = self._format_raw_udp(direction, payload_len)
        segment = TransportSegment(
            id=len(self.segments) + 1,
            total_segments=0,
            protocol=TransportProtocol.UDP,
            direction=direction,
            source_ip=src_ip,
            destination_ip=dst_ip,
            source_port=src_port,
            destination_port=dst_port,
            seq=0,
            ack=0,
            window=0,
            flags=[],
            payload_length=payload_len,
            application_event_id=app_event_id,
            client_state="N/A (UDP)",
            server_state="N/A (UDP)",
            summary=summary,
            raw_segment=raw_str,
            explanation=explanation,
            relative_time_ms=self._current_time_ms,
        )
        self.segments.append(segment)
        return segment

    def perform_handshake(self) -> Tuple[TransportSegment, TransportSegment, TransportSegment]:
        """
        Executes a 3-Way Handshake:
        1. Client -> Server: SYN (Seq=client_isn, Ack=0)
        2. Server -> Client: SYN-ACK (Seq=server_isn, Ack=client_isn+1)
        3. Client -> Server: ACK (Seq=client_isn+1, Ack=server_isn+1)
        Both transition to ESTABLISHED.
        """
        # 1. SYN
        s1 = self.send_client_tcp(
            flags=["SYN"],
            summary=f"TCP [SYN] Seq={self.client_seq} Win={self.window_size}",
            explanation=(
                f"Client initializes connection with SYN (Synchronize Sequence Numbers) to port {self.server_port}. "
                f"Client picks Initial Sequence Number (ISN) {self.client_seq} and advertises receive window {self.window_size} bytes."
            ),
        )

        # 2. SYN-ACK
        s2 = self.send_server_tcp(
            flags=["SYN", "ACK"],
            summary=f"TCP [SYN, ACK] Seq={self.server_seq} Ack={self.server_ack} Win={self.window_size}",
            explanation=(
                f"Server responds with SYN-ACK. It acknowledges the client's SYN by setting Ack={self.server_ack} (ISN+1), "
                f"and picks its own server ISN {self.server_seq}. Both sequence number spaces are now synchronized."
            ),
        )

        # 3. ACK (Completes 3-way handshake)
        self.client_state = TCPState.ESTABLISHED.value
        self.server_state = TCPState.ESTABLISHED.value
        s3 = self.send_client_tcp(
            flags=["ACK"],
            summary=f"TCP [ACK] Seq={self.client_seq} Ack={self.client_ack} Win={self.window_size}",
            explanation=(
                f"Client transmits ACK acknowledging server ISN (Ack={self.client_ack}). "
                f"The 3-Way Handshake is complete. Both client and server enter ESTABLISHED state and can now stream byte data."
            ),
        )

        return s1, s2, s3

    def perform_teardown(self) -> List[TransportSegment]:
        """
        Executes an orderly 4-Way TCP Teardown (RFC 793):
        1. Client -> Server: FIN-ACK (Client transitions to FIN-WAIT-1)
        2. Server -> Client: ACK (Server transitions to CLOSE-WAIT, Client transitions to FIN-WAIT-2)
        3. Server -> Client: FIN-ACK (Server transitions to LAST-ACK)
        4. Client -> Server: ACK (Client transitions to TIME-WAIT, Server transitions to CLOSED)
        """
        teardown_steps = []

        # 1. Client FIN-ACK
        s1 = self.send_client_tcp(
            flags=["FIN", "ACK"],
            summary=f"TCP [FIN, ACK] Seq={self.client_seq} Ack={self.client_ack}",
            explanation=(
                "Active Close: Client has finished sending application data and transmits FIN to close its send channel. "
                "Client enters FIN-WAIT-1."
            ),
        )
        teardown_steps.append(s1)

        # 2. Server ACK
        self.client_state = TCPState.FIN_WAIT_2.value
        self.server_state = TCPState.CLOSE_WAIT.value
        s2 = self.send_server_tcp(
            flags=["ACK"],
            summary=f"TCP [ACK] Seq={self.server_seq} Ack={self.server_ack}",
            explanation=(
                "Passive Close: Server acknowledges client FIN (Ack advances by 1). "
                "Server enters CLOSE-WAIT; client enters FIN-WAIT-2."
            ),
        )
        teardown_steps.append(s2)

        # 3. Server FIN-ACK
        s3 = self.send_server_tcp(
            flags=["FIN", "ACK"],
            summary=f"TCP [FIN, ACK] Seq={self.server_seq} Ack={self.server_ack}",
            explanation=(
                "Server concludes its own transmission and sends FIN to close its send channel. Server enters LAST-ACK."
            ),
        )
        teardown_steps.append(s3)

        # 4. Client ACK
        self.client_state = TCPState.TIME_WAIT.value
        s4 = self.send_client_tcp(
            flags=["ACK"],
            summary=f"TCP [ACK] Seq={self.client_seq} Ack={self.client_ack}",
            explanation=(
                "Client acknowledges server FIN. Client enters TIME-WAIT (waiting 2 * Maximum Segment Lifetime "
                "to ensure the final ACK arrives). Server enters CLOSED."
            ),
        )
        self.server_state = TCPState.CLOSED.value
        teardown_steps.append(s4)

        return teardown_steps


# ============================================================================
# Activity-Specific Transport Generators
# ============================================================================

def generate_browsing_transport_segments(
    app_steps: List[ProtocolStep], simulate_loss: bool = False
) -> List[TransportSegment]:
    """
    Generates transport layer segments for Web Browsing:
    1. UDP DNS Query (App Step 1)
    2. UDP DNS Response (App Step 2)
    3. TCP 3-Way Handshake (SYN, SYN-ACK, ACK)
    4. HTTP GET Request over TCP (App Step 3)
    5. TCP ACK for HTTP Request
    6. [Optional Retransmission if simulate_loss]
    7. HTTP 200 Response over TCP (App Step 4)
    8. TCP ACK for HTTP Response
    9. TCP 4-Way Teardown (FIN, ACK, FIN, ACK)
    """
    server_ip = "93.184.216.34"
    sim = TCPConnectionSimulator(server_ip=server_ip, server_port=80, client_isn=1000, server_isn=5000)

    # 1. DNS Query (UDP Port 53)
    sim.add_udp_datagram(
        Direction.CLIENT_TO_SERVER,
        src_port=54120,
        dst_port=53,
        payload_len=32,
        app_event_id=1,
        summary="UDP DNS Standard Query (Port 53)",
        explanation="DNS uses connectionless UDP on port 53 for fast single-packet resolution without handshake overhead.",
    )

    # 2. DNS Response (UDP Port 53)
    sim.add_udp_datagram(
        Direction.SERVER_TO_CLIENT,
        src_port=53,
        dst_port=54120,
        payload_len=48,
        app_event_id=2,
        summary="UDP DNS Standard Response: A Record",
        explanation="DNS server replies with UDP datagram containing the resolved IPv4 address.",
    )

    # 3. TCP 3-Way Handshake
    sim.perform_handshake()

    # 4. HTTP GET request transported as TCP Segment (App Step 3)
    http_req_len = len(app_steps[2].raw_message.encode("utf-8")) if len(app_steps) >= 3 else 312
    sim.send_client_tcp(
        flags=["ACK", "PSH"],
        payload_len=http_req_len,
        app_event_id=3,
        summary=f"TCP [PSH, ACK] HTTP GET Request ({http_req_len} bytes)",
        explanation=(
            f"The browser pushes the HTTP GET request ({http_req_len} bytes) into the TCP send buffer. "
            f"The PSH (Push) flag instructs the receiving TCP stack to pass data to the application without waiting for buffer fill."
        ),
    )

    # 5. Server acknowledges receipt of HTTP GET data
    sim.send_server_tcp(
        flags=["ACK"],
        payload_len=0,
        summary=f"TCP [ACK] Seq={sim.server_seq} Ack={sim.server_ack}",
        explanation=f"Server acknowledges receipt of {http_req_len} bytes of HTTP GET request (Ack={sim.server_ack}).",
    )

    # 6. Optional Packet Loss Simulation: illustrate timeout and retransmission
    if simulate_loss:
        sim.send_client_tcp(
            flags=["ACK", "PSH"],
            payload_len=http_req_len,
            app_event_id=3,
            summary=f"[RETRANSMISSION] TCP [PSH, ACK] Seq={sim.client_seq - http_req_len} ({http_req_len} bytes)",
            explanation="Educational Fault Simulation: Segment loss detected via Retransmission Timeout (RTO). Sender retransmits identical sequence.",
            retransmission=True,
        )

    # 7. HTTP 200 Response delivered via TCP (App Step 4)
    http_resp_len = len(app_steps[3].raw_message.encode("utf-8")) if len(app_steps) >= 4 else 580
    sim.send_server_tcp(
        flags=["ACK", "PSH"],
        payload_len=http_resp_len,
        app_event_id=4,
        summary=f"TCP [PSH, ACK] HTTP 200 Response Data ({http_resp_len} bytes)",
        explanation=f"Web server delivers HTTP response headers and HTML payload ({http_resp_len} bytes) across TCP byte stream.",
    )

    # 8. Client acknowledges receipt of HTTP Response data
    sim.send_client_tcp(
        flags=["ACK"],
        payload_len=0,
        summary=f"TCP [ACK] Seq={sim.client_seq} Ack={sim.client_ack}",
        explanation=f"Client acknowledges received HTTP response bytes (Ack={sim.client_ack}).",
    )

    # 9. TCP 4-Way Teardown
    sim.perform_teardown()

    # Finalize segment totals
    for s in sim.segments:
        s.total_segments = len(sim.segments)

    return sim.segments


def generate_mail_transport_segments(
    app_steps: List[ProtocolStep], simulate_loss: bool = False
) -> List[TransportSegment]:
    """
    Generates transport layer segments for SMTP Mail:
    1. TCP 3-Way Handshake to Port 25
    2. SMTP 220 Greeting in TCP segment (App Step 1)
    3. EHLO in TCP segment (App Step 2)
    4. 250 Capabilities in TCP segment (App Step 3)
    5. MAIL FROM in TCP segment (App Step 4)
    6. 250 Sender OK in TCP segment (App Step 5)
    7. RCPT TO in TCP segment (App Step 6)
    8. 250 Recipient OK in TCP segment (App Step 7)
    9. DATA in TCP segment (App Step 8)
    10. 354 Start Input in TCP segment (App Step 9)
    11. MIME Body & '.' in TCP segment (App Step 10)
    12. 250 Queued in TCP segment (App Step 11)
    13. QUIT in TCP segment (App Step 12)
    14. 221 Bye in TCP segment (App Step 13)
    15. TCP Teardown
    """
    sim = TCPConnectionSimulator(server_ip="198.51.100.25", server_port=25, client_isn=2000, server_isn=8000)

    # Handshake to Mail Port 25
    sim.perform_handshake()

    # Dialogue steps mapped directly to TCP PSH-ACK and ACK pairs
    dialogue_mappings = [
        (1, False, 64, "SMTP 220 Server Greeting Banner"),
        (2, True, 28, "SMTP EHLO Command"),
        (3, False, 142, "SMTP 250 Extension Advertisement"),
        (4, True, 36, "SMTP MAIL FROM Envelope"),
        (5, False, 42, "SMTP 250 Sender OK"),
        (6, True, 38, "SMTP RCPT TO Envelope"),
        (7, False, 44, "SMTP 250 Recipient OK"),
        (8, True, 6, "SMTP DATA Command"),
        (9, False, 48, "SMTP 354 Start Mail Input"),
        (10, True, 380, "SMTP MIME Headers + Email Body + '.'"),
        (11, False, 46, "SMTP 250 Queued for Delivery"),
        (12, True, 6, "SMTP QUIT Command"),
        (13, False, 52, "SMTP 221 Service Closing Transmission Channel"),
    ]

    for app_id, is_client, payload_len, label in dialogue_mappings:
        if is_client:
            sim.send_client_tcp(
                flags=["ACK", "PSH"],
                payload_len=payload_len,
                app_event_id=app_id,
                summary=f"TCP [PSH, ACK] {label} ({payload_len}B)",
                explanation=f"Client transmits {label} over persistent TCP connection to port 25.",
            )
            sim.send_server_tcp(
                flags=["ACK"],
                payload_len=0,
                summary=f"TCP [ACK] Ack={sim.server_ack}",
                explanation=f"Server acknowledges client command bytes.",
            )
        else:
            sim.send_server_tcp(
                flags=["ACK", "PSH"],
                payload_len=payload_len,
                app_event_id=app_id,
                summary=f"TCP [PSH, ACK] {label} ({payload_len}B)",
                explanation=f"MTA server replies with {label} over the TCP byte stream.",
            )
            sim.send_client_tcp(
                flags=["ACK"],
                payload_len=0,
                summary=f"TCP [ACK] Ack={sim.client_ack}",
                explanation=f"Client acknowledges server reply bytes.",
            )

    # Teardown
    sim.perform_teardown()

    for s in sim.segments:
        s.total_segments = len(sim.segments)

    return sim.segments


def generate_streaming_transport_segments(
    app_steps: List[ProtocolStep], simulate_loss: bool = False
) -> List[TransportSegment]:
    """
    Generates transport layer segments for Adaptive Video Streaming (HLS over HTTP/TCP):
    1. UDP DNS Resolution for CDN Edge (App Steps 1 & 2)
    2. TCP 3-Way Handshake with CDN Node (Port 80)
    3. HTTP Master Manifest Request & Segment Responses (App Steps 3 & 4)
    4. HTTP Variant Manifest Request & Segment Responses (App Steps 5 & 6)
    5. HTTP Segment 1042 Request & Chunk Data Transfer (App Steps 7 & 8)
    6. HTTP Segment 1043 Request & Chunk Data Transfer (App Steps 9 & 10)
    7. TCP Teardown
    """
    cdn_ip = "104.21.45.89"
    sim = TCPConnectionSimulator(server_ip=cdn_ip, server_port=80, client_isn=3000, server_isn=9000)

    # 1. DNS Query (UDP 53)
    sim.add_udp_datagram(
        Direction.CLIENT_TO_SERVER,
        src_port=58912,
        dst_port=53,
        payload_len=34,
        app_event_id=1,
        summary="UDP DNS Query: CDN Edge Address",
        explanation="Client queries DNS for CDN Edge node using standard UDP on port 53.",
    )

    # 2. DNS Response (UDP 53)
    sim.add_udp_datagram(
        Direction.SERVER_TO_CLIENT,
        src_port=53,
        dst_port=58912,
        payload_len=52,
        app_event_id=2,
        summary="UDP DNS Response: CDN Anycast IP",
        explanation="DNS server resolves CDN Anycast edge IP.",
    )

    # 3. TCP 3-Way Handshake
    sim.perform_handshake()

    # 4. Master Playlist GET (App Step 3 & 4)
    sim.send_client_tcp(
        flags=["ACK", "PSH"],
        payload_len=184,
        app_event_id=3,
        summary="TCP [PSH, ACK] GET master.m3u8",
        explanation="Client requests HLS master playlist via HTTP GET over established TCP stream.",
    )
    sim.send_server_tcp(
        flags=["ACK", "PSH"],
        payload_len=340,
        app_event_id=4,
        summary="TCP [PSH, ACK] 200 OK master.m3u8 (Multi-bitrate Variants)",
        explanation="CDN server delivers master manifest containing available stream profiles (360p, 720p, 1080p).",
    )
    sim.send_client_tcp(flags=["ACK"], payload_len=0, summary=f"TCP [ACK] Ack={sim.client_ack}")

    # 5. Media Variant Playlist GET (App Step 5 & 6)
    sim.send_client_tcp(
        flags=["ACK", "PSH"],
        payload_len=198,
        app_event_id=5,
        summary="TCP [PSH, ACK] GET variant playlist.m3u8",
        explanation="Player requests media segment playlist for chosen resolution.",
    )
    sim.send_server_tcp(
        flags=["ACK", "PSH"],
        payload_len=260,
        app_event_id=6,
        summary="TCP [PSH, ACK] 200 OK Media Segment Index",
        explanation="CDN responds with list of upcoming 4-second video chunk URIs.",
    )
    sim.send_client_tcp(flags=["ACK"], payload_len=0, summary=f"TCP [ACK] Ack={sim.client_ack}")

    # 6. Video Segment 1042 Request & Chunk Data (App Step 7 & 8)
    sim.send_client_tcp(
        flags=["ACK", "PSH"],
        payload_len=210,
        app_event_id=7,
        summary="TCP [PSH, ACK] GET segment_1042.ts",
        explanation="Player initiates download for video chunk 1042.",
    )
    # Deliver data in 2 consecutive TCP segments demonstrating byte stream segmentation!
    sim.send_server_tcp(
        flags=["ACK"],
        payload_len=1460,  # Max Segment Size (MSS)
        app_event_id=8,
        summary="TCP [ACK] segment_1042.ts Data Slice #1 (1460 bytes MSS)",
        explanation="TCP divides large media chunk into standard Maximum Segment Size (MSS 1460 bytes) packets.",
    )
    sim.send_server_tcp(
        flags=["ACK", "PSH"],
        payload_len=1120,
        app_event_id=8,
        summary="TCP [PSH, ACK] segment_1042.ts Data Slice #2 (1120 bytes)",
        explanation="Final data slice of segment 1042 delivered to client socket.",
    )
    sim.send_client_tcp(
        flags=["ACK"],
        payload_len=0,
        summary=f"TCP Cumulative [ACK] Ack={sim.client_ack}",
        explanation=f"Client issues cumulative ACK acknowledging all received segment 1042 bytes (Ack={sim.client_ack}).",
    )

    # 7. Video Segment 1043 Request & Chunk Data (App Step 9 & 10)
    sim.send_client_tcp(
        flags=["ACK", "PSH"],
        payload_len=210,
        app_event_id=9,
        summary="TCP [PSH, ACK] GET segment_1043.ts",
        explanation="Player pipelines next chunk request to prevent buffer underrun.",
    )
    sim.send_server_tcp(
        flags=["ACK"],
        payload_len=1460,
        app_event_id=10,
        summary="TCP [ACK] segment_1043.ts Data Slice #1 (1460 bytes MSS)",
        explanation="CDN server streams first MSS packet of segment 1043.",
    )
    sim.send_server_tcp(
        flags=["ACK", "PSH"],
        payload_len=1250,
        app_event_id=10,
        summary="TCP [PSH, ACK] segment_1043.ts Data Slice #2 (1250 bytes)",
        explanation="CDN server streams second packet of segment 1043.",
    )
    sim.send_client_tcp(
        flags=["ACK"],
        payload_len=0,
        summary=f"TCP Cumulative [ACK] Ack={sim.client_ack}",
        explanation=f"Client confirms receipt with cumulative ACK (Ack={sim.client_ack}).",
    )

    # 8. Teardown
    sim.perform_teardown()

    for s in sim.segments:
        s.total_segments = len(sim.segments)

    return sim.segments


def generate_transport_segments_for_activity(
    activity_type: ActivityType,
    app_steps: List[ProtocolStep],
    simulate_loss: bool = False,
) -> List[TransportSegment]:
    """Factory creating transport segments for any activity type."""
    if activity_type == ActivityType.BROWSING:
        return generate_browsing_transport_segments(app_steps, simulate_loss)
    elif activity_type == ActivityType.MAIL:
        return generate_mail_transport_segments(app_steps, simulate_loss)
    elif activity_type == ActivityType.STREAMING:
        return generate_streaming_transport_segments(app_steps, simulate_loss)
    else:
        raise ValueError(f"Unknown activity type: {activity_type}")


def link_application_and_transport_steps(
    app_steps: List[ProtocolStep], transport_segments: List[TransportSegment]
) -> None:
    """Populate bidirectional references between Application and Transport steps."""
    for step in app_steps:
        linked_ids = [s.id for s in transport_segments if s.application_event_id == step.step_id]
        step.transport_segment_ids = linked_ids


def calculate_transport_stats(
    segments: List[TransportSegment], app_steps: List[ProtocolStep]
) -> TransportStats:
    """Calculate live metrics from the simulation dataset."""
    total_packets = len(segments)
    tcp_segments = sum(1 for s in segments if s.protocol == TransportProtocol.TCP)
    application_messages = len(app_steps)
    total_bytes = sum(s.payload_length for s in segments)
    retransmissions = sum(1 for s in segments if s.retransmission)

    client_state = segments[-1].client_state if segments else TCPState.CLOSED.value
    server_state = segments[-1].server_state if segments else TCPState.LISTEN.value

    # Educational cwnd calculation based on packets transferred
    cwnd = min(16, max(1, (tcp_segments // 2)))

    return TransportStats(
        total_packets=total_packets,
        tcp_segments=tcp_segments,
        application_messages=application_messages,
        total_bytes=total_bytes,
        retransmissions=retransmissions,
        client_state=client_state,
        server_state=server_state,
        cwnd=cwnd,
    )
