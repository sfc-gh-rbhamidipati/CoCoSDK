"""
server.py — Starlette + Uvicorn backend bridging a React frontend to the Cortex Code Agent SDK.

Architecture:
    Browser (React) --POST /api/chat--> server.py --SDK--> Cortex Code Agent
    Browser          <--SSE stream-----  server.py <--async iter-- Agent responses

Endpoints:
    GET  /                — Serve interactive.html
    POST /api/chat        — Send a message, stream agent response via SSE
    POST /api/demo/run    — Run a demo script as subprocess, stream output via SSE
    GET  /api/sessions    — List active sessions (debug)
"""

import asyncio
import json
import os
import time
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse, PlainTextResponse
from starlette.routing import Route
from sse_starlette import EventSourceResponse

from cortex_code_agent_sdk import (
    CortexCodeSDKClient,
    CortexCodeAgentOptions,
    AssistantMessage,
    ResultMessage,
)
from cortex_code_agent_sdk.types import StreamEvent

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_DIR = os.environ.get("DEMO_PROJECT_DIR", str(Path(__file__).resolve().parent))

# Map demo names to their script filenames
DEMO_SCRIPTS = {
    "single_turn": "demo_single_turn.py",
    "multi_turn": "demo_multi_turn.py",
    "structured_output": "demo_structured_output.py",
    "chat_embed": "demo_chat_embed.py",
}

# Sessions idle longer than this are cleaned up (seconds)
SESSION_IDLE_TIMEOUT = 600  # 10 minutes

# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

# Each entry: {"client": CortexCodeSDKClient, "last_active": float}
_sessions: dict[str, dict] = {}
_sessions_lock = asyncio.Lock()


async def get_or_create_session(session_id: str) -> CortexCodeSDKClient:
    """Return an existing SDK client for session_id, or create a new one."""
    async with _sessions_lock:
        # Cleanup stale sessions on every access
        await _cleanup_stale_sessions_unlocked()

        entry = _sessions.get(session_id)
        if entry is not None:
            entry["last_active"] = time.time()
            return entry["client"]

        # Create a new session-based client
        client = CortexCodeSDKClient(
            CortexCodeAgentOptions(
                cwd=PROJECT_DIR,
                allowed_tools=["Read", "Bash"],
                include_partial_messages=True,
            )
        )
        # Enter the async context manager so the client is ready
        await client.__aenter__()

        _sessions[session_id] = {
            "client": client,
            "last_active": time.time(),
        }
        return client


async def _cleanup_stale_sessions_unlocked():
    """Remove sessions idle longer than SESSION_IDLE_TIMEOUT.

    Must be called while holding _sessions_lock.
    """
    now = time.time()
    stale_ids = [
        sid
        for sid, entry in _sessions.items()
        if now - entry["last_active"] > SESSION_IDLE_TIMEOUT
    ]
    for sid in stale_ids:
        entry = _sessions.pop(sid)
        try:
            await entry["client"].__aexit__(None, None, None)
        except Exception:
            pass  # best-effort cleanup


# ---------------------------------------------------------------------------
# GET / — Serve the HTML frontend
# ---------------------------------------------------------------------------

async def index(request: Request):
    html_path = Path(PROJECT_DIR) / "interactive.html"
    if not html_path.exists():
        return HTMLResponse(
            "<h2>Frontend not found</h2>"
            "<p><code>interactive.html</code> is missing from the project directory.</p>"
            "<p>The API endpoints are still available at <code>/api/chat</code>, "
            "<code>/api/demo/run</code>, and <code>/api/sessions</code>.</p>",
            status_code=404,
        )
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# POST /api/chat — Chat with the Cortex Code Agent, streamed via SSE
# ---------------------------------------------------------------------------

async def chat_handler(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    message = body.get("message")
    if not message:
        return JSONResponse({"error": "Missing 'message' field"}, status_code=400)

    session_id = body.get("session_id", "default")

    try:
        client = await get_or_create_session(session_id)
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to create SDK session: {exc}"},
            status_code=500,
        )

    async def event_generator():
        try:
            await client.query(message)

            async for msg in client.receive_response():
                if isinstance(msg, StreamEvent):
                    event = msg.event
                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield {
                                "event": "text",
                                "data": json.dumps({"text": delta["text"]}),
                            }

                elif isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if hasattr(block, "name"):
                            yield {
                                "event": "tool_call",
                                "data": json.dumps({
                                    "tool": block.name,
                                    "status": "calling",
                                }),
                            }

                elif isinstance(msg, ResultMessage):
                    yield {
                        "event": "done",
                        "data": json.dumps({"status": msg.subtype}),
                    }

        except Exception as exc:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(exc)}),
            }

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# POST /api/demo/run — Run a demo script as a subprocess, stream output via SSE
# ---------------------------------------------------------------------------

async def demo_run_handler(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    demo_name = body.get("demo")
    if demo_name not in DEMO_SCRIPTS:
        return JSONResponse(
            {
                "error": f"Unknown demo '{demo_name}'. "
                f"Valid options: {', '.join(sorted(DEMO_SCRIPTS))}"
            },
            status_code=400,
        )

    script_path = os.path.join(PROJECT_DIR, DEMO_SCRIPTS[demo_name])
    if not os.path.exists(script_path):
        return JSONResponse(
            {"error": f"Demo script not found: {DEMO_SCRIPTS[demo_name]}"},
            status_code=404,
        )

    async def event_generator():
        try:
            # Immediate feedback while subprocess starts
            yield {
                "event": "output",
                "data": json.dumps({"line": f"▶ Launching {DEMO_SCRIPTS[demo_name]}..."}),
            }

            proc = await asyncio.create_subprocess_exec(
                "python3", "-u", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=PROJECT_DIR,
            )

            # Stream stdout line by line
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip("\n")
                yield {
                    "event": "output",
                    "data": json.dumps({"line": decoded}),
                }

            exit_code = await proc.wait()
            yield {
                "event": "done",
                "data": json.dumps({"exit_code": exit_code}),
            }

        except Exception as exc:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(exc)}),
            }

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# GET /api/sessions — List active sessions (debug)
# ---------------------------------------------------------------------------

async def sessions_handler(request: Request):
    async with _sessions_lock:
        now = time.time()
        sessions_info = {
            sid: {
                "idle_seconds": round(now - entry["last_active"]),
                "last_active": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(entry["last_active"])
                ),
            }
            for sid, entry in _sessions.items()
        }
    return JSONResponse({"sessions": sessions_info, "count": len(sessions_info)})


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

routes = [
    Route("/", index, methods=["GET"]),
    Route("/api/chat", chat_handler, methods=["POST"]),
    Route("/api/demo/run", demo_run_handler, methods=["POST"]),
    Route("/api/sessions", sessions_handler, methods=["GET"]),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    ),
]

app = Starlette(routes=routes, middleware=middleware)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print(f"Starting server on http://0.0.0.0:8765")
    print(f"Project directory: {PROJECT_DIR}")
    print(f"Available demos: {', '.join(sorted(DEMO_SCRIPTS))}")
    uvicorn.run(app, host="0.0.0.0", port=8765)
