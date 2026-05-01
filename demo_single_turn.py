"""
Demo 1: Single-Turn Agent
--------------------------
Sends one prompt to the Cortex Code Agent SDK and streams the response.
The agent reads threat_report.py, finds bugs, and fixes them automatically.
"""

import asyncio
from cortex_code_agent_sdk import query, AssistantMessage, ResultMessage, CortexCodeAgentOptions
from cortex_code_agent_sdk.types import StreamEvent


async def main():
    print("=" * 60)
    print("  Cortex Code Agent SDK - Single Turn Demo")
    print("  Task: Find and fix bugs in threat_report.py")
    print("=" * 60)
    print()

    async for message in query(
        prompt="Review threat_report.py for bugs in the security event pipeline. Fix any issues you find.",
        options=CortexCodeAgentOptions(
            cwd=".",
            allowed_tools=["Read", "Edit", "Bash"],
            include_partial_messages=True,
        ),
    ):
        if isinstance(message, StreamEvent):
            event = message.event
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    print(delta.get("text", ""), end="", flush=True)

        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "name"):
                    print(f"\n>> Tool call: {block.name}")

        elif isinstance(message, ResultMessage):
            print(f"\n\nDone: {message.subtype}")


if __name__ == "__main__":
    asyncio.run(main())
