"""
WebSocket Manager for Application & Transport Layer Activity & Protocol Visualizer.
Manages per-client connection state, progressive auto-play ticker loop,
interactive playback controls (Pause, Resume, Next, Prev, Replay, Seek),
and coordinated Application <-> Transport layer event synchronization.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect

from app.protocol_models import (
    ActivityType,
    ProtocolStep,
    TransportSegment,
    WSClientAction,
    WSClientMessage,
    WSServerEvent,
    WSServerMessage,
)
from app.protocol_simulator import (
    generate_steps_for_activity,
    get_step_summaries,
)
from app.transport_simulator import (
    calculate_transport_stats,
    generate_transport_segments_for_activity,
    link_application_and_transport_steps,
)

logger = logging.getLogger("websocket_manager")


class PlaybackSession:
    """Manages protocol exchange state and playback ticker for a single WebSocket connection."""

    def __init__(self, websocket: WebSocket, step_interval_sec: float = 1.3):
        self.websocket = websocket
        self.step_interval_sec = step_interval_sec
        self.activity_type: Optional[ActivityType] = None
        self.active_layer: str = "application"
        self.steps: List[ProtocolStep] = []
        self.transport_segments: List[TransportSegment] = []
        self.current_step_index: int = 0  # 1-indexed (1 to len(self.steps))
        self.current_transport_index: int = 0  # 1-indexed (1 to len(self.transport_segments))
        self.is_playing: bool = False
        self.simulate_loss: bool = False
        self._ticker_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def send_event(self, message: WSServerMessage) -> None:
        """Serialize and transmit server message to client."""
        try:
            raw_json = message.model_dump_json()
            await self.websocket.send_text(raw_json)
        except Exception as exc:
            logger.debug(f"Failed to send message over WebSocket: {exc}")

    def _cancel_ticker(self) -> None:
        if self._ticker_task and not self._ticker_task.done():
            self._ticker_task.cancel()
            self._ticker_task = None

    async def handle_disconnect(self) -> None:
        """Clean up background tasks on client disconnect."""
        self._cancel_ticker()
        self.is_playing = False

    async def handle_client_message(self, data_str: str) -> None:
        """Parse incoming JSON client payload and dispatch to appropriate control handler."""
        try:
            data = json.loads(data_str)
            client_msg = WSClientMessage(**data)
        except Exception as exc:
            await self.send_event(
                WSServerMessage(
                    event=WSServerEvent.ERROR,
                    error_message=f"Invalid message format: {exc}",
                )
            )
            return

        async with self._lock:
            action = client_msg.action

            if action == WSClientAction.START_ACTIVITY:
                await self._action_start(client_msg.activity_type, client_msg.params)
            elif action == WSClientAction.PAUSE:
                await self._action_pause()
            elif action == WSClientAction.RESUME:
                await self._action_resume()
            elif action == WSClientAction.NEXT_STEP:
                layer = (client_msg.params or {}).get("layer", self.active_layer) if client_msg.params else self.active_layer
                await self._action_next(layer=layer)
            elif action == WSClientAction.PREV_STEP:
                layer = (client_msg.params or {}).get("layer", self.active_layer) if client_msg.params else self.active_layer
                await self._action_prev(layer=layer)
            elif action == WSClientAction.REPLAY:
                await self._action_replay()
            elif action == WSClientAction.SEEK:
                target_transport = (client_msg.params or {}).get("target_transport_id") if client_msg.params else None
                await self._action_seek(client_msg.target_step, target_transport)
            elif action == WSClientAction.TOGGLE_LOSS:
                await self._action_toggle_loss(client_msg.simulate_loss)
            elif action == WSClientAction.SWITCH_LAYER:
                layer = (client_msg.params or {}).get("layer", "application") if client_msg.params else "application"
                await self._action_switch_layer(layer)

    async def _action_start(
        self, activity_type: Optional[ActivityType], params: Optional[Dict[str, Any]]
    ) -> None:
        if not activity_type:
            await self.send_event(
                WSServerMessage(
                    event=WSServerEvent.ERROR,
                    error_message="Missing activity_type in start_activity request",
                )
            )
            return

        self._cancel_ticker()
        self.activity_type = activity_type

        # 1. Generate Application Layer Steps
        self.steps = generate_steps_for_activity(activity_type, params)

        # 2. Generate Transport Layer Segments & Cross-Link
        self.transport_segments = generate_transport_segments_for_activity(
            activity_type, self.steps, self.simulate_loss
        )
        link_application_and_transport_steps(self.steps, self.transport_segments)

        self.current_step_index = 1
        self.current_transport_index = 1
        self.is_playing = True

        summaries = get_step_summaries(self.steps)
        initial_step = self.steps[0]
        initial_transport = self.transport_segments[0] if self.transport_segments else None
        stats = calculate_transport_stats(self.transport_segments, self.steps)

        # 3. Announce new session initialization with both layers
        await self.send_event(
            WSServerMessage(
                event=WSServerEvent.SESSION_INITIALIZED,
                activity_type=self.activity_type,
                current_step_index=1,
                total_steps=len(self.steps),
                is_playing=True,
                step=initial_step,
                all_steps_summary=summaries,
                transport_segments=self.transport_segments,
                current_transport_segment=initial_transport,
                transport_stats=stats,
                log_message=f"Initialized {activity_type.value.upper()} exchange ({len(self.steps)} app steps, {len(self.transport_segments)} transport segments)",
                status_text=f"Active: {activity_type.value.capitalize()} in progress",
            )
        )

        # 4. Start progressive background ticker loop
        self._ticker_task = asyncio.create_task(self._playback_loop())

    def _sync_indices_from_step(self) -> None:
        """Align transport segment pointer with active application step."""
        if 1 <= self.current_step_index <= len(self.steps):
            step = self.steps[self.current_step_index - 1]
            if step.transport_segment_ids:
                target_id = step.transport_segment_ids[0]
                self.current_transport_index = target_id

    def _sync_step_from_transport(self) -> None:
        """Align application step pointer with active transport segment."""
        if 1 <= self.current_transport_index <= len(self.transport_segments):
            seg = self.transport_segments[self.current_transport_index - 1]
            if seg.application_event_id:
                self.current_step_index = seg.application_event_id

    async def _playback_loop(self) -> None:
        """Progressively advances through protocol exchange with calibrated delay."""
        try:
            while self.is_playing:
                await asyncio.sleep(self.step_interval_sec)

                async with self._lock:
                    if not self.is_playing:
                        break

                    if self.active_layer == "transport" and self.transport_segments:
                        if self.current_transport_index < len(self.transport_segments):
                            self.current_transport_index += 1
                            self._sync_step_from_transport()

                            is_last = self.current_transport_index == len(self.transport_segments)
                            if is_last:
                                self.is_playing = False

                            await self._push_current_step(
                                log_note=f"Segment #{self.current_transport_index}",
                                status_text="Completed" if is_last else f"Segment {self.current_transport_index}/{len(self.transport_segments)}",
                            )
                            if is_last:
                                break
                        else:
                            self.is_playing = False
                            break
                    else:
                        if self.current_step_index < len(self.steps):
                            self.current_step_index += 1
                            self._sync_indices_from_step()

                            is_last = self.current_step_index == len(self.steps)
                            if is_last:
                                self.is_playing = False

                            await self._push_current_step(
                                log_note=f"Step #{self.current_step_index}",
                                status_text="Completed" if is_last else f"Step {self.current_step_index}/{len(self.steps)}",
                            )
                            if is_last:
                                break
                        else:
                            self.is_playing = False
                            break
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception(f"Error in playback loop: {exc}")

    async def _action_pause(self) -> None:
        self._cancel_ticker()
        self.is_playing = False
        await self.send_event(
            WSServerMessage(
                event=WSServerEvent.PLAYBACK_STATE,
                activity_type=self.activity_type,
                current_step_index=self.current_step_index,
                total_steps=len(self.steps),
                is_playing=False,
                log_message="Playback paused by user",
                status_text="Paused",
            )
        )

    async def _action_resume(self) -> None:
        if not self.steps:
            return

        if self.active_layer == "transport" and self.transport_segments:
            if self.current_transport_index >= len(self.transport_segments):
                self.current_step_index = 1
                self.current_transport_index = 1
                await self._push_current_step("Replaying exchange from beginning")
        else:
            if self.current_step_index >= len(self.steps):
                self.current_step_index = 1
                self.current_transport_index = 1
                await self._push_current_step("Replaying exchange from beginning")

        self.is_playing = True
        self._cancel_ticker()
        self._ticker_task = asyncio.create_task(self._playback_loop())

        await self.send_event(
            WSServerMessage(
                event=WSServerEvent.PLAYBACK_STATE,
                activity_type=self.activity_type,
                current_step_index=self.current_step_index,
                total_steps=len(self.steps),
                is_playing=True,
                log_message="Playback resumed",
                status_text="Playing",
            )
        )

    async def _action_next(self, layer: str = "application") -> None:
        if not self.steps:
            return
        self._cancel_ticker()
        self.is_playing = False

        if layer == "transport" and self.transport_segments:
            if self.current_transport_index < len(self.transport_segments):
                self.current_transport_index += 1
                self._sync_step_from_transport()
                await self._push_current_step(f"Stepped transport to segment #{self.current_transport_index}")
            else:
                await self._send_end_of_exchange_state("Already at final transport segment")
        else:
            if self.current_step_index < len(self.steps):
                self.current_step_index += 1
                self._sync_indices_from_step()
                await self._push_current_step(f"Stepped application to step #{self.current_step_index}")
            else:
                await self._send_end_of_exchange_state("Already at final application step")

    async def _action_prev(self, layer: str = "application") -> None:
        if not self.steps:
            return
        self._cancel_ticker()
        self.is_playing = False

        if layer == "transport" and self.transport_segments:
            if self.current_transport_index > 1:
                self.current_transport_index -= 1
                self._sync_step_from_transport()
                await self._push_current_step(f"Stepped transport back to segment #{self.current_transport_index}")
            else:
                await self._send_end_of_exchange_state("Already at first transport segment")
        else:
            if self.current_step_index > 1:
                self.current_step_index -= 1
                self._sync_indices_from_step()
                await self._push_current_step(f"Stepped application back to step #{self.current_step_index}")
            else:
                await self._send_end_of_exchange_state("Already at first application step")

    async def _action_replay(self) -> None:
        if not self.steps:
            return
        self._cancel_ticker()
        self.current_step_index = 1
        self.current_transport_index = 1
        self.is_playing = True

        await self._push_current_step("Replaying exchange from beginning")
        self._ticker_task = asyncio.create_task(self._playback_loop())

    async def _action_seek(
        self, target_step: Optional[int], target_transport: Optional[int] = None
    ) -> None:
        if not self.steps:
            return
        self._cancel_ticker()
        self.is_playing = False

        if target_transport is not None and 1 <= target_transport <= len(self.transport_segments):
            self.current_transport_index = target_transport
            self._sync_step_from_transport()
            await self._push_current_step(f"Jumped to transport segment #{target_transport}")
        elif target_step is not None and 1 <= target_step <= len(self.steps):
            self.current_step_index = target_step
            self._sync_indices_from_step()
            await self._push_current_step(f"Jumped to application step #{target_step}")

    async def _action_toggle_loss(self, simulate_loss: Optional[bool]) -> None:
        if simulate_loss is not None:
            self.simulate_loss = simulate_loss
        else:
            self.simulate_loss = not self.simulate_loss

        if self.activity_type and self.steps:
            self.transport_segments = generate_transport_segments_for_activity(
                self.activity_type, self.steps, self.simulate_loss
            )
            link_application_and_transport_steps(self.steps, self.transport_segments)
            stats = calculate_transport_stats(self.transport_segments, self.steps)

            current_step = self.steps[self.current_step_index - 1]
            current_transport = (
                self.transport_segments[self.current_transport_index - 1]
                if 1 <= self.current_transport_index <= len(self.transport_segments)
                else None
            )

            await self.send_event(
                WSServerMessage(
                    event=WSServerEvent.STEP_UPDATE,
                    activity_type=self.activity_type,
                    current_step_index=self.current_step_index,
                    total_steps=len(self.steps),
                    is_playing=self.is_playing,
                    step=current_step,
                    transport_segments=self.transport_segments,
                    current_transport_segment=current_transport,
                    transport_stats=stats,
                    log_message=f"Network condition: Packet loss simulation {'ENABLED' if self.simulate_loss else 'DISABLED'}",
                    status_text=f"Loss Sim: {'ON' if self.simulate_loss else 'OFF'}",
                )
            )

    async def _send_end_of_exchange_state(self, message: str) -> None:
        await self.send_event(
            WSServerMessage(
                event=WSServerEvent.PLAYBACK_STATE,
                activity_type=self.activity_type,
                current_step_index=self.current_step_index,
                total_steps=len(self.steps),
                is_playing=False,
                log_message=message,
                status_text="End of exchange" if "final" in message else "Start of exchange",
            )
        )

    async def _push_current_step(self, log_note: str, status_text: Optional[str] = None) -> None:
        step_data = self.steps[self.current_step_index - 1]
        transport_data = (
            self.transport_segments[self.current_transport_index - 1]
            if 1 <= self.current_transport_index <= len(self.transport_segments)
            else (self.transport_segments[0] if self.transport_segments else None)
        )
        stats = calculate_transport_stats(self.transport_segments, self.steps)

        await self.send_event(
            WSServerMessage(
                event=WSServerEvent.STEP_UPDATE,
                activity_type=self.activity_type,
                current_step_index=self.current_step_index,
                total_steps=len(self.steps),
                is_playing=self.is_playing,
                step=step_data,
                current_transport_segment=transport_data,
                transport_stats=stats,
                log_message=f"[{step_data.protocol.value}] {log_note}: {step_data.summary}",
                status_text=status_text or f"Step {self.current_step_index}/{len(self.steps)}",
            )
        )

    async def _action_switch_layer(self, layer: str) -> None:
        """Track active layer on server to drive layer-aware auto-play stepping."""
        self.active_layer = layer
        # If switching to transport and playback is running, restart the loop
        # so it immediately starts ticking in the correct layer direction.
        if self.is_playing:
            self._cancel_ticker()
            self._ticker_task = asyncio.create_task(self._playback_loop())

