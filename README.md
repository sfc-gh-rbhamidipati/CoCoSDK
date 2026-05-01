# Cortex Code Agent SDK — Interactive Demo

A self-contained interactive slide deck and live demo application for the [Cortex Code Agent SDK](https://docs.snowflake.com/en/user-guide/cortex-code-agent-sdk/cortex-code-agent-sdk). Built for technical presentations — run it locally, walk through the slides, and execute live demos directly from the deck.

## What's Inside

| File | Description |
|------|-------------|
| `interactive.html` | Interactive slide deck (React, runs in-browser) |
| `server.py` | Starlette backend — bridges the slide deck to the SDK |
| `demo_single_turn.py` | Demo 1: Single-prompt bug fix |
| `demo_multi_turn.py` | Demo 2: Multi-turn session with context reuse |
| `demo_structured_output.py` | Demo 3: JSON schema enforcement on agent output |
| `demo_chat_embed.py` | Demo 4: Embedding the SDK into a chat backend |
| `threat_report.py` | Sample Python file the agent analyzes during demos |
| `run_demo.sh` | Launch script (shell) |
| `Start Demo.command` | Launch script (double-click on macOS) |

## Prerequisites

1. **Cortex Code CLI** — the SDK requires the CLI to be installed.

   ```bash
   curl -LsS https://ai.snowflake.com/static/cc-scripts/install.sh | sh
   ```

2. **Snowflake connection** — configure a connection in `~/.snowflake/connections.toml`. If you already have one set up for the Snowflake CLI (`snow`), it works here too. Otherwise, run `cortex` and the setup wizard will walk you through it.

   ```toml
   # ~/.snowflake/connections.toml
   [my-connection]
   account = "myorg-myaccount"
   user = "myuser"
   authenticator = "externalbrowser"
   ```

3. **Python 3.10+** with the following packages:

   ```bash
   pip install cortex-code-agent-sdk starlette uvicorn sse-starlette
   ```

## Quick Start

**Option A — Shell script:**

```bash
chmod +x run_demo.sh
./run_demo.sh
```

**Option B — Double-click (macOS):**

Double-click `Start Demo.command`. It will open Terminal, start the server, and launch your browser.

**Option C — Manual:**

```bash
python3 server.py
# Open http://localhost:8765 in your browser
```

The server starts on `http://localhost:8765`. The slide deck opens automatically.

## How It Works

```
Browser (React slides) → POST /api/chat → server.py → Cortex Code Agent SDK → Snowflake
                       ← SSE stream ←──────────────── Agent responses
```

- **Slides** — navigate with arrow keys, spacebar, or the on-screen controls.
- **Live demos** — click "Run Live" on any demo slide to execute the corresponding Python script. Output streams into an embedded terminal.
- **Live chat** — the flagship slide (Demo 4) includes a working chat interface powered by the SDK. Ask security questions and watch the agent reason in real time.

## Demo Flow

The slides tell a progressive story:

1. **What is the Cortex Code Agent SDK** — positioning and capabilities
2. **Architecture Fit** — how the SDK fits into an existing platform
3. **Demo 1: Single-Turn** — one prompt, agent reads/fixes code autonomously
4. **Demo 2: Multi-Turn** — session context reuse across conversation turns
5. **Demo 3: Structured Output** — JSON schema enforcement for machine-readable results
6. **Demo 4: Chat Embedding** — flagship demo with live chat interface
7. **Governance & Cost** — RBAC, resource monitors, auth patterns
8. **Unstructured Data** — Cortex Search + Cortex Agent for combined queries
9. **Next Steps** — action items and resources

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve the slide deck |
| `POST` | `/api/chat` | Send a message to the agent (SSE stream) |
| `POST` | `/api/demo/run` | Run a demo script (SSE stream) |
| `GET` | `/api/sessions` | List active SDK sessions (debug) |

## Running the Demo Scripts Standalone

Each demo script can be run independently outside the slide deck:

```bash
python3 demo_single_turn.py
python3 demo_multi_turn.py
python3 demo_structured_output.py
python3 demo_chat_embed.py
```

## Tests

```bash
pip install pytest
pytest tests/
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DEMO_PROJECT_DIR` | Script directory | Working directory for the agent |

The server runs on port `8765` by default. To change it, edit the `PORT` variable in `run_demo.sh` or `server.py`.

## Resources

- [Cortex Code Agent SDK docs](https://docs.snowflake.com/en/user-guide/cortex-code-agent-sdk/cortex-code-agent-sdk)
- [SDK Python reference](https://docs.snowflake.com/en/user-guide/cortex-code-agent-sdk/python-sdk-reference)
- [SDK TypeScript reference](https://docs.snowflake.com/en/user-guide/cortex-code-agent-sdk/typescript-sdk-reference)
- [Cortex Code CLI setup](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli)
- [Cortex Agents REST API](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-rest-api)

## License

Internal use — Snowflake.
