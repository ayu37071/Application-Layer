"""
Pydantic Data Models for Application & Transport Layer Activity & Protocol Visualizer.
Defines schemas for application layer steps, transport layer TCP/UDP segments,
highlight fields, playback states, statistics, and bidirectional WebSocket messages.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Direction(str, Enum):
    CLIENT_TO_SERVER = "client_to_server"
    SERVER_TO_CLIENT = "server_to_client"


class ProtocolType(str, Enum):
    DNS = "DNS"
    HTTP = "HTTP"
    SMTP = "SMTP"


class TransportProtocol(str, Enum):
    TCP = "TCP"
    UDP = "UDP"


class ActivityType(str, Enum):
    BROWSING = "browsing"
    MAIL = "mail"
    STREAMING = "streaming"


class TCPState(str, Enum):
    CLOSED = "CLOSED"
    LISTEN = "LISTEN"
    SYN_SENT = "SYN-SENT"
    SYN_RECEIVED = "SYN-RECEIVED"
    ESTABLISHED = "ESTABLISHED"
    FIN_WAIT_1 = "FIN-WAIT-1"
    FIN_WAIT_2 = "FIN-WAIT-2"
    CLOSE_WAIT = "CLOSE-WAIT"
    LAST_ACK = "LAST-ACK"
    TIME_WAIT = "TIME-WAIT"


class HighlightField(BaseModel):
    name: str = Field(..., description="Field label e.g., 'Method', 'Status Code', 'Transaction ID'")
    value: str = Field(..., description="Extracted value e.g., 'GET', '200 OK', '0x4f12'")
    description: str = Field(..., description="Networking significance of this field")


class ProtocolStep(BaseModel):
    step_id: int = Field(..., description="1-indexed sequence number in this exchange")
    total_steps: int = Field(..., description="Total count of steps in this activity session")
    protocol: ProtocolType = Field(..., description="Application layer protocol name")
    direction: Direction = Field(..., description="Packet direction")
    sender: str = Field(..., description="Sender descriptor e.g. Client (192.168.1.50:52412)")
    receiver: str = Field(..., description="Receiver descriptor e.g. Web Server (93.184.216.34:80)")
    summary: str = Field(..., description="Brief one-line summary of this wire exchange")
    raw_message: str = Field(..., description="Wire-accurate ASCII representation with line breaks")
    highlighted_fields: List[HighlightField] = Field(
        default_factory=list,
        description="Key fields highlighted for student comprehension"
    )
    explanation: str = Field(..., description="Pedagogical explanation of what is happening")
    relative_time_ms: int = Field(..., description="Relative offset in milliseconds since activity trigger")
    transport_segment_ids: List[int] = Field(
        default_factory=list,
        description="IDs of linked transport segments carrying this application message"
    )


class TransportSegment(BaseModel):
    id: int = Field(..., description="1-indexed transport segment sequence ID")
    total_segments: int = Field(..., description="Total transport segments in session")
    protocol: TransportProtocol = Field(default=TransportProtocol.TCP, description="TCP or UDP")
    direction: Direction = Field(..., description="client_to_server or server_to_client")
    source_ip: str = Field(..., description="Source IPv4 address")
    destination_ip: str = Field(..., description="Destination IPv4 address")
    source_port: int = Field(..., description="Source port number")
    destination_port: int = Field(..., description="Destination port number")
    seq: int = Field(..., description="TCP Sequence Number")
    ack: int = Field(..., description="TCP Acknowledgement Number")
    window: int = Field(default=64240, description="Advertised receive window size in bytes")
    flags: List[str] = Field(default_factory=list, description="TCP control flags e.g. ['SYN'], ['ACK', 'PSH']")
    payload_length: int = Field(default=0, description="Transport payload length in bytes")
    application_event_id: Optional[int] = Field(
        default=None,
        description="Linked Application Layer step_id, if this segment transports an application message"
    )
    client_state: str = Field(default=TCPState.CLOSED.value, description="Client TCP connection state")
    server_state: str = Field(default=TCPState.LISTEN.value, description="Server TCP connection state")
    summary: str = Field(..., description="One-line transport summary e.g. 'TCP [SYN] Seq=1000 Win=64240'")
    raw_segment: str = Field(..., description="Formatted ASCII TCP/UDP header dissection")
    explanation: str = Field(..., description="Pedagogical explanation of TCP transport mechanics")
    relative_time_ms: int = Field(default=0, description="Relative timestamp offset in milliseconds")
    retransmission: bool = Field(default=False, description="True if segment simulates a retransmission")


class TransportStats(BaseModel):
    total_packets: int = 0
    tcp_segments: int = 0
    application_messages: int = 0
    total_bytes: int = 0
    retransmissions: int = 0
    client_state: str = TCPState.CLOSED.value
    server_state: str = TCPState.LISTEN.value
    cwnd: int = 1  # In segments (MSS)


class StepSummary(BaseModel):
    step_id: int
    protocol: ProtocolType
    direction: Direction
    summary: str
    transport_segment_ids: List[int] = Field(default_factory=list)


class WSClientAction(str, Enum):
    START_ACTIVITY = "start_activity"
    PAUSE = "pause"
    RESUME = "resume"
    NEXT_STEP = "next_step"
    PREV_STEP = "prev_step"
    REPLAY = "replay"
    SEEK = "seek"
    TOGGLE_LOSS = "toggle_loss"


class WSClientMessage(BaseModel):
    action: WSClientAction
    activity_type: Optional[ActivityType] = None
    params: Optional[Dict[str, Any]] = None
    target_step: Optional[int] = None
    simulate_loss: Optional[bool] = None


class WSServerEvent(str, Enum):
    SESSION_INITIALIZED = "session_initialized"
    STEP_UPDATE = "step_update"
    PLAYBACK_STATE = "playback_state"
    ACTIVITY_LOG = "activity_log"
    ERROR = "error"


class WSServerMessage(BaseModel):
    event: WSServerEvent
    activity_type: Optional[ActivityType] = None
    current_step_index: int = 0
    total_steps: int = 0
    is_playing: bool = False
    step: Optional[ProtocolStep] = None
    all_steps_summary: Optional[List[StepSummary]] = None
    transport_segments: Optional[List[TransportSegment]] = None
    current_transport_segment: Optional[TransportSegment] = None
    transport_stats: Optional[TransportStats] = None
    log_message: Optional[str] = None
    status_text: Optional[str] = None
    error_message: Optional[str] = None
