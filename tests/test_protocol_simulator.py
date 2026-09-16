"""
Automated Pytest Suite for Application Layer Activity & Protocol Visualizer.
Verifies RFC adherence, sequence integrity, header fields, and WebSocket state transitions.
"""

import json
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.protocol_models import (
    ActivityType,
    Direction,
    ProtocolType,
    WSClientAction,
)
from app.protocol_simulator import (
    generate_browsing_steps,
    generate_mail_steps,
    generate_streaming_steps,
    generate_steps_for_activity,
    get_step_summaries,
)


def test_browsing_flow():
    """Verify the 4-step Browsing exchange: DNS Query -> DNS Resp -> HTTP Req -> HTTP Resp."""
    url = "http://gaia.cs.umass.edu/kurose_ross/interactive/"
    steps = generate_browsing_steps(url)

    assert len(steps) == 4, f"Expected exactly 4 steps, got {len(steps)}"

    # Step 1: DNS Query
    s1 = steps[0]
    assert s1.step_id == 1
    assert s1.protocol == ProtocolType.DNS
    assert s1.direction == Direction.CLIENT_TO_SERVER
    assert "gaia.cs.umass.edu" in s1.summary
    assert "Transaction ID" in [f.name for f in s1.highlighted_fields]
    assert "Standard query" in s1.raw_message

    # Step 2: DNS Response
    s2 = steps[1]
    assert s2.step_id == 2
    assert s2.protocol == ProtocolType.DNS
    assert s2.direction == Direction.SERVER_TO_CLIENT
    assert "Resolved IP" in [f.name for f in s2.highlighted_fields]
    assert "No error" in s2.raw_message or "NoError" in s2.raw_message

    # Step 3: HTTP GET Request
    s3 = steps[2]
    assert s3.step_id == 3
    assert s3.protocol == ProtocolType.HTTP
    assert s3.direction == Direction.CLIENT_TO_SERVER
    assert "GET /kurose_ross/interactive/ HTTP/1.1" in s3.raw_message
    assert "Host: gaia.cs.umass.edu" in s3.raw_message
    assert any(f.name == "Method" and f.value == "GET" for f in s3.highlighted_fields)

    # Step 4: HTTP 200 OK Response
    s4 = steps[3]
    assert s4.step_id == 4
    assert s4.protocol == ProtocolType.HTTP
    assert s4.direction == Direction.SERVER_TO_CLIENT
    assert "HTTP/1.1 200 OK" in s4.raw_message
    assert "Content-Type: text/html" in s4.raw_message
    assert any(f.name == "Status Code" and "200 OK" in f.value for f in s4.highlighted_fields)


def test_mail_flow():
    """Verify the 13-step SMTP transaction state machine (RFC 5321)."""
    params = {
        "to": "prof.kurose@cs.umass.edu",
        "from": "student@university.edu",
        "subject": "Lab 2 Submission",
        "body": "Hello Professor,\nPlease find our submission.\nThank you.",
    }
    steps = generate_mail_steps(params)

    assert len(steps) == 13, f"Expected 13 SMTP steps, got {len(steps)}"

    expected_commands = [
        (1, ProtocolType.SMTP, Direction.SERVER_TO_CLIENT, "220"),
        (2, ProtocolType.SMTP, Direction.CLIENT_TO_SERVER, "EHLO"),
        (3, ProtocolType.SMTP, Direction.SERVER_TO_CLIENT, "250"),
        (4, ProtocolType.SMTP, Direction.CLIENT_TO_SERVER, "MAIL FROM:<student@university.edu>"),
        (5, ProtocolType.SMTP, Direction.SERVER_TO_CLIENT, "250"),
        (6, ProtocolType.SMTP, Direction.CLIENT_TO_SERVER, "RCPT TO:<prof.kurose@cs.umass.edu>"),
        (7, ProtocolType.SMTP, Direction.SERVER_TO_CLIENT, "250"),
        (8, ProtocolType.SMTP, Direction.CLIENT_TO_SERVER, "DATA"),
        (9, ProtocolType.SMTP, Direction.SERVER_TO_CLIENT, "354"),
        (10, ProtocolType.SMTP, Direction.CLIENT_TO_SERVER, "Subject: Lab 2 Submission"),
        (11, ProtocolType.SMTP, Direction.SERVER_TO_CLIENT, "queued as"),
        (12, ProtocolType.SMTP, Direction.CLIENT_TO_SERVER, "QUIT"),
        (13, ProtocolType.SMTP, Direction.SERVER_TO_CLIENT, "221"),
    ]

    for idx, proto, direction, keyword in expected_commands:
        step = steps[idx - 1]
        assert step.step_id == idx
        assert step.protocol == proto
        assert step.direction == direction
        assert keyword in step.raw_message, f"Step {idx} missing keyword '{keyword}' in message:\n{step.raw_message}"

    # Verify message termination single dot on its own line
    step10 = steps[9]
    assert "\r\n.\n" in step10.raw_message or "\r\n." in step10.raw_message or step10.raw_message.endswith(".")


def test_streaming_flow():
    """Verify the 10-step HLS Adaptive Bitrate Streaming exchange."""
    params = {"quality": "1080p"}
    steps = generate_streaming_steps(params)

    assert len(steps) == 10, f"Expected 10 streaming steps, got {len(steps)}"

    # Check DNS steps
    assert steps[0].protocol == ProtocolType.DNS
    assert steps[1].protocol == ProtocolType.DNS

    # Check Master Playlist steps
    assert "master.m3u8" in steps[2].raw_message
    assert "#EXT-X-STREAM-INF" in steps[3].raw_message

    # Check Media Playlist step for selected quality (1080p)
    assert "1080p/playlist.m3u8" in steps[4].raw_message
    assert "#EXTINF:4.000" in steps[5].raw_message

    # Check Segment requests and responses
    assert "segment_1042.ts" in steps[6].raw_message
    assert "video/mp2t" in steps[7].raw_message
    assert "segment_1043.ts" in steps[8].raw_message
    assert "video/mp2t" in steps[9].raw_message


def test_factory_and_summaries():
    """Verify general factory and summary generation utilities."""
    browsing_steps = generate_steps_for_activity(ActivityType.BROWSING, {"url": "http://test.edu"})
    summaries = get_step_summaries(browsing_steps)
    assert len(summaries) == 4
    assert summaries[0].protocol == ProtocolType.DNS
    assert summaries[2].protocol == ProtocolType.HTTP


def test_web_routes():
    """Verify HTTP GET endpoints / and /health."""
    client = TestClient(app)

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "Application Layer Activity &amp; Protocol Visualizer" in res_index.text
    assert 'id="activity-panel"' in res_index.text
    assert 'id="protocol-panel"' in res_index.text


def test_websocket_lifecycle():
    """Verify bidirectional WebSocket synchronization and playback actions."""
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        # Trigger browsing activity
        ws.send_text(
            json.dumps({
                "action": "start_activity",
                "activity_type": "browsing",
                "params": {"url": "http://gaia.cs.umass.edu"}
            })
        )

        # Receive session_initialized
        data = ws.receive_text()
        msg = json.loads(data)
        assert msg["event"] == "session_initialized"
        assert msg["total_steps"] == 4
        assert msg["current_step_index"] == 1
        assert msg["step"]["protocol"] == "DNS"

        # Pause playback
        ws.send_text(json.dumps({"action": "pause"}))
        data_pause = ws.receive_text()
        msg_pause = json.loads(data_pause)
        assert msg_pause["event"] == "playback_state"
        assert msg_pause["is_playing"] is False

        # Next Step
        ws.send_text(json.dumps({"action": "next_step"}))
        data_next = ws.receive_text()
        msg_next = json.loads(data_next)
        assert msg_next["event"] == "step_update"
        assert msg_next["current_step_index"] == 2

        # Prev Step
        ws.send_text(json.dumps({"action": "prev_step"}))
        data_prev = ws.receive_text()
        msg_prev = json.loads(data_prev)
        assert msg_prev["event"] == "step_update"
        assert msg_prev["current_step_index"] == 1

        # Seek to step 4
        ws.send_text(json.dumps({"action": "seek", "target_step": 4}))
        data_seek = ws.receive_text()
        msg_seek = json.loads(data_seek)
        assert msg_seek["event"] == "step_update"
        assert msg_seek["current_step_index"] == 4
        assert msg_seek["step"]["protocol"] == "HTTP"
