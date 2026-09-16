"""
Pydantic Data Models for Application Layer Activity & Protocol Visualizer.
Defines schemas for protocol events, highlight fields, playback states,
and bidirectional WebSocket messages.
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


class ActivityType(str, Enum):
    BROWSING = "browsing"
    MAIL = "mail"
    STREAMING = "streaming"


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


class StepSummary(BaseModel):
    step_id: int
    protocol: ProtocolType
    direction: Direction
    summary: str


class WSClientAction(str, Enum):
    START_ACTIVITY = "start_activity"
    PAUSE = "pause"
    RESUME = "resume"
    NEXT_STEP = "next_step"
    PREV_STEP = "prev_step"
    REPLAY = "replay"
    SEEK = "seek"


class WSClientMessage(BaseModel):
    action: WSClientAction
    activity_type: Optional[ActivityType] = None
    params: Optional[Dict[str, Any]] = None
    target_step: Optional[int] = None


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
    log_message: Optional[str] = None
    status_text: Optional[str] = None
    error_message: Optional[str] = None
