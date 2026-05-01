"""
Demo 4: Chat Embedding Simulation
------------------------------------
Shows how the Cortex Code Agent SDK can serve as the backend for an internal
chat tool. Uses CortexCodeSDKClient (session-based, multi-turn)
so each user question builds on the previous context — exactly how a chat
backend maintains conversation state.

The demo runs 3 pre-loaded questions about the threat data in threat_report.py,
streaming each response as it arrives.

Extending this demo:
  - Add sql_execute to allowed_tools for live Snowflake queries (Text2SQL).
  - Integrate Cortex Search for unstructured data (PDFs, PowerPoints, wiki pages).
  - Combine both for hybrid queries: "What threats correlate with the anomalies
    described in last week's incident report?" — the agent uses SQL for structured
    data and Cortex Search for document retrieval in a single turn.
"""

import asyncio
from cortex_code_agent_sdk import (
    CortexCodeSDKClient,
    CortexCodeAgentOptions,
    AssistantMessage,
    ResultMessage,
)
from cortex_code_agent_sdk.types import StreamEvent


# Pre-loaded example questions a chat user might ask about threat data.
# In production, these come from the chat UI's message stream.
EXAMPLE_QUESTIONS = [
    "Which threat campaigns in threat_report.py had the highest escalation rate?",
    "Summarize the overall security posture from the data in threat_report.py.",
    "What campaigns need immediate attention based on false positive ratios?",
]


async def stream_response(client):
    """Stream and print all messages until the agent finishes."""
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
            print(f"\n[Agent finished: {msg.subtype}]")


async def main():
    print("=" * 60)
    print("  Cortex Code Agent SDK - Chat Embedding Demo")
    print("  Simulates a chat backend powered by the SDK")
    print("=" * 60)

    # CortexCodeSDKClient maintains session state across queries,
    # so the agent remembers what it read in earlier turns — just
    # like a real chat backend would carry conversation context.
    async with CortexCodeSDKClient(
        CortexCodeAgentOptions(
            cwd=".",
            allowed_tools=["Read", "Bash"],
            include_partial_messages=True,
        )
    ) as client:

        for i, question in enumerate(EXAMPLE_QUESTIONS, 1):
            print(f"\n{'─' * 60}")
            print(f"  User question {i}/{len(EXAMPLE_QUESTIONS)}:")
            print(f"  {question}")
            print(f"{'─' * 60}\n")

            await client.query(question)
            await stream_response(client)
            print()  # blank line between responses


if __name__ == "__main__":
    asyncio.run(main())
