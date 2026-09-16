"""
FastAPI Application Entry Point for Application Layer Activity & Protocol Visualizer.
Mounts static assets, renders the dual-panel web dashboard, and hosts the WebSocket endpoint.
"""

import logging
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.websocket_manager import PlaybackSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Application Layer Activity & Protocol Visualizer",
    description="Interactive educational dashboard visualizing DNS, HTTP, and SMTP protocol mechanics in real time.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def index_view(request: Request):
    """Serve the primary two-panel dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_name": "Application Layer Activity & Protocol Visualizer"},
    )


@app.get("/health")
async def health_check():
    """Health status endpoint."""
    return {"status": "ok", "service": "Application Layer Activity & Protocol Visualizer"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Bidirectional WebSocket connection for progressive protocol visualization."""
    await websocket.accept()
    session = PlaybackSession(websocket)
    logger.info("New WebSocket client connected")

    try:
        while True:
            data_text = await websocket.receive_text()
            await session.handle_client_message(data_text)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
        await session.handle_disconnect()
    except Exception as exc:
        logger.warning(f"WebSocket session terminated with exception: {exc}")
        await session.handle_disconnect()
