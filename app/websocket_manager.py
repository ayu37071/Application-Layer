"""
WebSocket Manager for Application Layer Activity & Protocol Visualizer.
Manages per-client connection state, progressive auto-play ticker loop,
and interactive playback controls (Pause, Resume, Next, Prev, Replay, Seek).
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect

from app.protocol_models import (
    ActivityType,
    ProtocolStep,
    WSClientAction,
    WSClientMessage,
    WSServerEvent,
    WSServerMessage,
)
from app.protocol_simulator import (
    generate_steps_for_activity,
    get_step_summaries,
)

logger = logging.getLogger("websocket_manager")


class PlaybackSession:
    """Manages protocol exchange state and playback ticker for a single WebSocket connection."""

    def __init__(self, websocket: WebSocket, step_interval_sec: float = 1.3):
        self.websocket = websocket
        self.step_interval_sec = step_interval_sec
        self.activity_type: Optional[ActivityType] = None
        self.steps: List[ProtocolStep] = []
        self.current_step_index: int = 0  # 1-indexed when active (1 to N)
        self.is_playing: bool = False
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
                await self._action_next()
            elif action == WSClientAction.PREV_STEP:
                await self._action_prev()
            elif action == WSClientAction.REPLAY:
                await self._action_replay()
            elif action == WSClientAction.SEEK:
                await self._action_seek(client_msg.target_step)

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
        self.steps = generate_steps_for_activity(activity_type, params)
        self.current_step_index = 1
        self.is_playing = True

        summaries = get_step_summaries(self.steps)
        initial_step = self.steps[0]

        # 1. Announce new session initialization with full steps outline
        await self.send_event(
            WSServerMessage(
                event=WSServerEvent.SESSION_INITIALIZED,
                activity_type=self.activity_type,
                current_step_index=1,
                total_steps=len(self.steps),
                is_playing=True,
                step=initial_step,
                all_steps_summary=summaries,
                log_message=f"Initialized {activity_type.value.upper()} exchange ({len(self.steps)} steps)",
                status_text=f"Active: {activity_type.value.capitalize()} in progress",
            )
        )

        # 2. Start background ticker for progressive steps
        self._ticker_task = asyncio.create_task(self._playback_loop())

    async def _playback_loop(self) -> None:
        """Progressively advances through protocol steps with calibrated delay."""
        try:
            while self.is_playing and self.current_step_index < len(self.steps):
                await asyncio.sleep(self.step_interval_sec)

                async with self._lock:
                    if not self.is_playing:
                        break
                    if self.current_step_index < len(self.steps):
                        self.current_step_index += 1
                        step_data = self.steps[self.current_step_index - 1]
                        is_last = self.current_step_index == len(self.steps)
                        if is_last:
                            self.is_playing = False

                        await self.send_event(
                            WSServerMessage(
                                event=WSServerEvent.STEP_UPDATE,
                                activity_type=self.activity_type,
                                current_step_index=self.current_step_index,
                                total_steps=len(self.steps),
                                is_playing=self.is_playing,
                                step=step_data,
                                log_message=f"Step {self.current_step_index}/{len(self.steps)}: {step_data.summary}",
                                status_text="Completed" if is_last else "Streaming steps...",
                            )
                        )
                        if is_last:
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

        if self.current_step_index >= len(self.steps):
            # Rewind if finished
            self.current_step_index = 1
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

    async def _action_next(self) -> None:
        if not self.steps:
            return
        self._cancel_ticker()
        self.is_playing = False

        if self.current_step_index < len(self.steps):
            self.current_step_index += 1
            await self._push_current_step(f"Stepped forward to {self.current_step_index}")
        else:
            await self.send_event(
                WSServerMessage(
                    event=WSServerEvent.PLAYBACK_STATE,
                    activity_type=self.activity_type,
                    current_step_index=self.current_step_index,
                    total_steps=len(self.steps),
                    is_playing=False,
                    log_message="Already at the final step",
                    status_text="End of exchange",
                )
            )

    async def _action_prev(self) -> None:
        if not self.steps:
            return
        self._cancel_ticker()
        self.is_playing = False

        if self.current_step_index > 1:
            self.current_step_index -= 1
            await self._push_current_step(f"Stepped back to {self.current_step_index}")
        else:
            await self.send_event(
                WSServerMessage(
                    event=WSServerEvent.PLAYBACK_STATE,
                    activity_type=self.activity_type,
                    current_step_index=self.current_step_index,
                    total_steps=len(self.steps),
                    is_playing=False,
                    log_message="Already at the first step",
                    status_text="Start of exchange",
                )
            )

    async def _action_replay(self) -> None:
        if not self.steps:
            return
        self._cancel_ticker()
        self.current_step_index = 1
        self.is_playing = True

        await self._push_current_step("Replaying exchange from beginning")
        self._ticker_task = asyncio.create_task(self._playback_loop())

    async def _action_seek(self, target_step: Optional[int]) -> None:
        if not self.steps or target_step is None:
            return
        self._cancel_ticker()
        self.is_playing = False

        if 1 <= target_step <= len(self.steps):
            self.current_step_index = target_step
            await self._push_current_step(f"Jumped to step {target_step}")

    async def _push_current_step(self, log_note: str) -> None:
        step_data = self.steps[self.current_step_index - 1]
        await self.send_event(
            WSServerMessage(
                event=WSServerEvent.STEP_UPDATE,
                activity_type=self.activity_type,
                current_step_index=self.current_step_index,
                total_steps=len(self.steps),
                is_playing=self.is_playing,
                step=step_data,
                log_message=f"[{step_data.protocol.value}] {log_note}: {step_data.summary}",
                status_text=f"Step {self.current_step_index}/{len(self.steps)}",
            )
        )
