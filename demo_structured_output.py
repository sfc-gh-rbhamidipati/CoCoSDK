"""
Demo 3: Structured Output
---------------------------
Forces the agent to return a response matching a JSON Schema.
Useful for integrating agent results into downstream systems.
"""

import asyncio
import json
from cortex_code_agent_sdk import query, AssistantMessage, ResultMessage, CortexCodeAgentOptions
from cortex_code_agent_sdk.types import StreamEvent


THREAT_ASSESSMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "file": {"type": "string", "description": "The file that was reviewed"},
        "threats_found": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "line": {"type": "integer"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "description": {"type": "string"},
                    "remediation": {"type": "string"},
                },
                "required": ["line", "severity", "description", "remediation"],
            },
        },
        "overall_risk": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
        },
        "summary": {"type": "string"},
    },
    "required": ["file", "threats_found", "overall_risk", "summary"],
}


def extract_json(text):
    """Extract the first valid JSON object from text that may contain reasoning around it."""
    # Try the full text first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Walk through the string and try parsing from every '{' character
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj = json.loads(text[i:])
                return obj
            except json.JSONDecodeError:
                # Try to find where this object ends by using the raw decoder
                decoder = json.JSONDecoder()
                try:
                    obj, _ = decoder.raw_decode(text, i)
                    return obj
                except json.JSONDecodeError:
                    continue
    raise ValueError("No JSON object found in agent response")


async def main():
    print("=" * 60)
    print("  Cortex Code Agent SDK - Structured Output Demo")
    print("  Agent returns a machine-readable threat assessment")
    print("=" * 60)
    print()

    result_text = ""

    # Consume the full stream without breaking early to avoid cancel-scope errors
    async for message in query(
        prompt="Review threat_report.py for security issues. Return a structured threat assessment.",
        options=CortexCodeAgentOptions(
            cwd=".",
            allowed_tools=["Read"],
            include_partial_messages=True,
            output_format={
                "type": "json_schema",
                "schema": THREAT_ASSESSMENT_SCHEMA,
            },
        ),
    ):
        if isinstance(message, StreamEvent):
            event = message.event
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    result_text += text
                    print(text, end="", flush=True)

        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text") and not result_text:
                    result_text += block.text

        elif isinstance(message, ResultMessage):
            pass  # let the iterator end naturally

    # Parse and pretty-print the structured result
    if result_text:
        assessment = extract_json(result_text)
        print(f"File reviewed:  {assessment['file']}")
        print(f"Overall risk:   {assessment['overall_risk'].upper()}")
        print(f"Summary:        {assessment['summary']}")
        print(f"\nThreats found ({len(assessment['threats_found'])}):")
        for i, threat in enumerate(assessment["threats_found"], 1):
            print(f"\n  {i}. [Line {threat['line']}] ({threat['severity'].upper()})")
            print(f"     {threat['description']}")
            print(f"     Remediation: {threat['remediation']}")
    else:
        print("No structured output received.")


if __name__ == "__main__":
    asyncio.run(main())
