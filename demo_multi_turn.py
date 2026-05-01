"""
Demo 2: Multi-Turn Session
----------------------------
Shows how to maintain context across multiple prompts.
The agent remembers what it read in the first turn and builds on it in the second.
"""

import asyncio
from cortex_code_agent_sdk import (
    CortexCodeSDKClient,
    CortexCodeAgentOptions,
    AssistantMessage,
    ResultMessage,
)
from cortex_code_agent_sdk.types import StreamEvent


async def stream_response(client):
    """Stream and print all messages until the result is received."""
    async for msg in client.receive_response():
        if isinstance(msg, StreamEvent):
            event = msg.event
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    print(delta.get("text", ""), end="", flush=True)
        elif isinstance(msg, AssistantMessage):
            for block in msg.content:
                if hasattr(block, "name"):
                    print(f"\n>> Tool call: {block.name}")
        elif isinstance(msg, ResultMessage):
            print(f"\n\nDone: {msg.subtype}")


async def main():
    print("=" * 60)
    print("  Cortex Code Agent SDK - Multi-Turn Demo")
    print("  The agent remembers context between turns")
    print("=" * 60)

    async with CortexCodeSDKClient(
        CortexCodeAgentOptions(
            cwd=".",
            allowed_tools=["Read", "Edit", "Bash"],
            include_partial_messages=True,
        )
    ) as client:

        # --- Turn 1: Understand the code ---
        print("\n--- Turn 1: Summarize the security event pipeline ---\n")
        await client.query(
            "Summarize what threat_report.py does and what security event schema it expects."
        )
        await stream_response(client)

        # --- Turn 2: Build on previous context ---
        print("\n\n--- Turn 2: Add anomaly detection (agent already knows the code) ---\n")
        await client.query(
            "Now add a function that flags anomalous threat campaigns where the "
            "escalation rate exceeds 2x the average, and write tests for it."
        )
        await stream_response(client)


if __name__ == "__main__":
    asyncio.run(main())
