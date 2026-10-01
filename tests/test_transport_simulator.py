"""
Automated Pytest Suite for Assignment 2 Transport Layer Protocol Simulator.
Verifies TCP 3-Way Handshake, Sequence/ACK arithmetic, TCP State Machine,
Teardown, Activity mappings (Browsing, Mail, Streaming), Bidirectional Sync,
and WebSocket Transport payloads.
"""

import json
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.protocol_models import (
    ActivityType,
    Direction,
    ProtocolType,
    TCPState,
    TransportProtocol,
)
from app.protocol_simulator import generate_steps_for_activity
from app.transport_simulator import (
    TCPConnectionSimulator,
    calculate_transport_stats,
    generate_browsing_transport_segments,
    generate_mail_transport_segments,
    generate_streaming_transport_segments,
    generate_transport_segments_for_activity,
    link_application_and_transport_steps,
)


def test_tcp_handshake():
    """Verify standard TCP 3-way handshake mechanics, flags, and sequence tracking."""
    sim = TCPConnectionSimulator(client_isn=1000, server_isn=5000)
    s1, s2, s3 = sim.perform_handshake()

    # Segment 1: SYN
    assert s1.protocol == TransportProtocol.TCP
    assert s1.direction == Direction.CLIENT_TO_SERVER
    assert s1.flags == ["SYN"]
    assert s1.seq == 1000
    assert s1.ack == 0
    assert s1.client_state == TCPState.SYN_SENT.value
    assert s1.server_state == TCPState.SYN_RECEIVED.value

    # Segment 2: SYN-ACK
    assert s2.protocol == TransportProtocol.TCP
    assert s2.direction == Direction.SERVER_TO_CLIENT
    assert s2.flags == ["SYN", "ACK"]
    assert s2.seq == 5000
    assert s2.ack == 1001  # Acknowledges client SYN (1000 + 1)

    # Segment 3: ACK
    assert s3.protocol == TransportProtocol.TCP
    assert s3.direction == Direction.CLIENT_TO_SERVER
    assert s3.flags == ["ACK"]
    assert s3.seq == 1001
    assert s3.ack == 5001  # Acknowledges server SYN (5000 + 1)
    assert s3.client_state == TCPState.ESTABLISHED.value
    assert s3.server_state == TCPState.ESTABLISHED.value


def test_tcp_seq_ack_arithmetic():
    """Verify payload sequence advancement, SYN/FIN byte consumption, and cumulative ACKs."""
    sim = TCPConnectionSimulator(client_isn=1000, server_isn=5000)
    sim.perform_handshake()

    # Client is at seq 1001, server at seq 5001
    assert sim.client_seq == 1001
    assert sim.server_seq == 5001

    # Client transmits 500 bytes of HTTP GET data
    d1 = sim.send_client_tcp(flags=["ACK", "PSH"], payload_len=500)
    assert d1.seq == 1001
    assert d1.ack == 5001
    assert d1.payload_length == 500
    # Next expected client sequence must be 1001 + 500 = 1501
    assert sim.client_seq == 1501

    # Server sends pure ACK
    a1 = sim.send_server_tcp(flags=["ACK"], payload_len=0)
    assert a1.seq == 5001
    assert a1.ack == 1501  # Acknowledges all 500 bytes received

    # Server replies with 800 bytes of HTTP response data
    d2 = sim.send_server_tcp(flags=["ACK", "PSH"], payload_len=800)
    assert d2.seq == 5001
    assert d2.ack == 1501
    assert d2.payload_length == 800
    # Next expected server sequence must be 5001 + 800 = 5801
    assert sim.server_seq == 5801

    # Client sends pure ACK
    a2 = sim.send_client_tcp(flags=["ACK"], payload_len=0)
    assert a2.seq == 1501
    assert a2.ack == 5801


def test_tcp_teardown():
    """Verify 4-Way TCP connection termination and state transitions."""
    sim = TCPConnectionSimulator(client_isn=1000, server_isn=5000)
    sim.perform_handshake()
    teardown_segs = sim.perform_teardown()

    assert len(teardown_segs) == 4

    fin1, ack1, fin2, ack2 = teardown_segs

    # 1. Client FIN
    assert "FIN" in fin1.flags
    assert fin1.direction == Direction.CLIENT_TO_SERVER
    assert fin1.client_state == TCPState.FIN_WAIT_1.value

    # 2. Server ACK
    assert "ACK" in ack1.flags
    assert ack1.direction == Direction.SERVER_TO_CLIENT
    assert ack1.server_state == TCPState.CLOSE_WAIT.value
    assert ack1.client_state == TCPState.FIN_WAIT_2.value

    # 3. Server FIN
    assert "FIN" in fin2.flags
    assert fin2.direction == Direction.SERVER_TO_CLIENT
    assert fin2.server_state == TCPState.LAST_ACK.value

    # 4. Client ACK
    assert "ACK" in ack2.flags
    assert ack2.direction == Direction.CLIENT_TO_SERVER
    assert ack2.client_state == TCPState.TIME_WAIT.value
    assert sim.server_state == TCPState.CLOSED.value


def test_browsing_transport_mapping():
    """Verify that Web Browsing flow accurately maps DNS (UDP), Handshake, HTTP over TCP, and Teardown."""
    app_steps = generate_steps_for_activity(ActivityType.BROWSING, {"url": "http://gaia.cs.umass.edu"})
    segments = generate_browsing_transport_segments(app_steps)

    assert len(segments) >= 9

    # DNS over UDP
    assert segments[0].protocol == TransportProtocol.UDP
    assert segments[0].application_event_id == 1
    assert segments[1].protocol == TransportProtocol.UDP
    assert segments[1].application_event_id == 2

    # Handshake
    assert segments[2].flags == ["SYN"]
    assert segments[3].flags == ["SYN", "ACK"]
    assert segments[4].flags == ["ACK"]

    # HTTP GET over TCP
    get_seg = next(s for s in segments if s.application_event_id == 3)
    assert "PSH" in get_seg.flags
    assert get_seg.payload_length > 0
    assert get_seg.destination_port == 80

    # HTTP 200 over TCP
    resp_seg = next(s for s in segments if s.application_event_id == 4)
    assert "PSH" in resp_seg.flags
    assert resp_seg.payload_length > 0
    assert resp_seg.source_port == 80


def test_mail_transport_mapping():
    """Verify SMTP over TCP mapping and command-by-command delivery."""
    app_steps = generate_steps_for_activity(ActivityType.MAIL, {"to": "prof@edu.org"})
    segments = generate_mail_transport_segments(app_steps)

    assert len(segments) >= 20

    # Port 25
    assert segments[0].destination_port == 25

    # Check that SMTP commands are linked
    linked_app_ids = {s.application_event_id for s in segments if s.application_event_id is not None}
    for app_id in range(1, 14):
        assert app_id in linked_app_ids, f"SMTP Step {app_id} not mapped to transport segment"


def test_streaming_transport_mapping():
    """Verify HLS media streaming over TCP with segmented chunk transfers."""
    app_steps = generate_steps_for_activity(ActivityType.STREAMING, {"quality": "720p"})
    segments = generate_streaming_transport_segments(app_steps)

    # Check for chunk segmentation (multiple segments carrying step 8 and step 10)
    seg8_transports = [s for s in segments if s.application_event_id == 8]
    assert len(seg8_transports) >= 2, "Expected multiple TCP segments delivering media chunk 1042"

    seg10_transports = [s for s in segments if s.application_event_id == 10]
    assert len(seg10_transports) >= 2, "Expected multiple TCP segments delivering media chunk 1043"


def test_cross_layer_linking_and_stats():
    """Verify bidirectional synchronization linking and stats calculation."""
    app_steps = generate_steps_for_activity(ActivityType.BROWSING, {"url": "http://example.edu"})
    segments = generate_transport_segments_for_activity(ActivityType.BROWSING, app_steps)
    link_application_and_transport_steps(app_steps, segments)

    # Every app step should have at least one transport segment ID
    for step in app_steps:
        assert len(step.transport_segment_ids) > 0, f"App Step {step.step_id} missing transport link"

    # Verify calculated stats
    stats = calculate_transport_stats(segments, app_steps)
    assert stats.total_packets == len(segments)
    assert stats.tcp_segments > 0
    assert stats.application_messages == 4
    assert stats.total_bytes > 0
    assert stats.retransmissions == 0


def test_network_fault_retransmission():
    """Verify simulated packet loss triggers a retransmission segment."""
    app_steps = generate_steps_for_activity(ActivityType.BROWSING, {"url": "http://example.edu"})
    segments_normal = generate_browsing_transport_segments(app_steps, simulate_loss=False)
    segments_loss = generate_browsing_transport_segments(app_steps, simulate_loss=True)

    assert len(segments_loss) == len(segments_normal) + 1
    retransmit_seg = next(s for s in segments_loss if s.retransmission)
    assert retransmit_seg.retransmission is True
    assert "[RETRANSMISSION]" in retransmit_seg.summary


def test_websocket_transport_synchronization():
    """Verify WebSocket server delivers coordinated application and transport events."""
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        # Start browsing activity
        ws.send_text(
            json.dumps({
                "action": "start_activity",
                "activity_type": "browsing",
                "params": {"url": "http://gaia.cs.umass.edu"}
            })
        )

        init_msg = json.loads(ws.receive_text())
        assert init_msg["event"] == "session_initialized"
        assert "transport_segments" in init_msg
        assert len(init_msg["transport_segments"]) > 0
        assert "transport_stats" in init_msg
        assert init_msg["current_transport_segment"] is not None

        # Pause
        ws.send_text(json.dumps({"action": "pause"}))
        pause_msg = json.loads(ws.receive_text())
        assert pause_msg["event"] == "playback_state"

        # Toggle simulated loss
        ws.send_text(json.dumps({"action": "toggle_loss", "simulate_loss": True}))
        loss_msg = json.loads(ws.receive_text())
        assert loss_msg["event"] == "step_update"
        assert any(s["retransmission"] for s in loss_msg["transport_segments"])
