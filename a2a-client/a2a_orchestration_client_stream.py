import asyncio
import json
import os
from typing import Any, Optional
from uuid import uuid4
import httpx
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import (
    MessageSendParams,
    SendStreamingMessageRequest,
)


def get_user_query() -> str:
    return input("\nUser Query:  ")


# request and stream of events
"""
Request payload JSON:
{
  "message": {
    "role": "user",
    "parts": [
      {
        "type": "text",
        "text": "weather info bA sate"
      }
    ],
    "message_id": "72eeeabb46234d4a9e4947e0fd6a7488"
  }
}

[send] streaming request id=417a129c5c0f4738b8d616491c714522
{'id': '417a129c5c0f4738b8d616491c714522', 'jsonrpc': '2.0', 'result': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'history': [{'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'kind': 'message', 'messageId': '72eeeabb46234d4a9e4947e0fd6a7488', 'parts': [{'kind': 'text', 'text': 'weather info bA sate'}], 'role': 'user', 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}], 'id': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03', 'kind': 'task', 'status': {'state': 'submitted'}}}
{'id': '417a129c5c0f4738b8d616491c714522', 'jsonrpc': '2.0', 'result': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'final': False, 'kind': 'status-update', 'status': {'message': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'kind': 'message', 'messageId': '25fb9636-2644-44db-b19f-9163ff7c5c6f', 'parts': [{'kind': 'text', 'text': 'Processing your request'}], 'role': 'agent', 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}, 'state': 'working'}, 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}}
{'id': '417a129c5c0f4738b8d616491c714522', 'jsonrpc': '2.0', 'result': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'final': False, 'kind': 'status-update', 'status': {'message': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'kind': 'message', 'messageId': '8ed40ff4-5560-49f0-8f1a-804cea82ad33', 'parts': [{'kind': 'text', 'text': 'Processing your request'}], 'role': 'agent', 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}, 'state': 'working'}, 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}}
{'id': '417a129c5c0f4738b8d616491c714522', 'jsonrpc': '2.0', 'result': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'final': False, 'kind': 'status-update', 'status': {'message': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'kind': 'message', 'messageId': '220883f4-3b2c-40b4-9019-519473589961', 'parts': [{'kind': 'text', 'text': 'Processing your request'}], 'role': 'agent', 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}, 'state': 'working'}, 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}}
{'id': '417a129c5c0f4738b8d616491c714522', 'jsonrpc': '2.0', 'result': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'final': False, 'kind': 'status-update', 'status': {'message': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'kind': 'message', 'messageId': '28dda7ab-9746-4f60-96ca-ccf8e3fe9fd7', 'parts': [{'kind': 'text', 'text': 'Processing your request'}], 'role': 'agent', 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}, 'state': 'working'}, 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}}
{'id': '417a129c5c0f4738b8d616491c714522', 'jsonrpc': '2.0', 'result': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'final': False, 'kind': 'status-update', 'status': {'message': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'kind': 'message', 'messageId': '4f4ce0d4-a8e2-4408-8d83-e3b1b68d3d5c', 'parts': [{'kind': 'text', 'text': 'Processing your request'}], 'role': 'agent', 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}, 'state': 'working'}, 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}}
{'id': '417a129c5c0f4738b8d616491c714522', 'jsonrpc': '2.0', 'result': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'final': False, 'kind': 'status-update', 'status': {'message': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'kind': 'message', 'messageId': '10d6faab-02b9-434f-a259-847bdad22f4c', 'parts': [{'kind': 'text', 'text': 'Processing your request'}], 'role': 'agent', 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}, 'state': 'working'}, 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}}
{'id': '417a129c5c0f4738b8d616491c714522', 'jsonrpc': '2.0', 'result': {'append': False, 'artifact': {'artifactId': 'd3d6374d-24e0-49d5-9a8b-c7cb78ed7bc4', 'description': 'Result of request to agent.', 'name': 'current_result', 'parts': [{'kind': 'text', 'text': 'It seems you are asking for weather alerts in the German state of Bavaria (BY). Let me get that information for you.There is a severe thunderstorm warning for Bavaria (BY). A severe thunderstorm is approaching the area, and it is advised to take cover immediately. Please stay safe and take necessary precautions.'}]}, 'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'kind': 'artifact-update', 'lastChunk': True, 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}}
{'id': '417a129c5c0f4738b8d616491c714522', 'jsonrpc': '2.0', 'result': {'contextId': 'f0909c95-719b-4124-a14b-94416c421f65', 'final': True, 'kind': 'status-update', 'status': {'state': 'completed'}, 'taskId': 'af9edb30-e0cd-4f0b-8786-47a7fe04ff03'}}

In next request , contextId will be same
last_context_id:::: bd24425867ef4a21b870691c38751b88
Request payload JSON:
{
  "message": {
    "role": "user",
    "parts": [
      {
        "type": "text",
        "text": "BAYERN State weather info"
      }
    ],
    "message_id": "0e221606324e4693b9da23ae06171ea1",
    "context_id": "bd24425867ef4a21b870691c38751b88"
  }
}

"""


def format_stream_event(evt: dict) -> Optional[str]:
    """Return 'status: <state or kind>\\n<text>' from an A2A stream event."""
    res = evt.get("result") or {}
    kind = res.get("kind")

    # Helper to join any text parts
    def join_text(parts):
        return "\n".join(
            p.get("text", "")
            for p in (parts or [])
            if isinstance(p, dict) and p.get("kind") == "text" and p.get("text")
        ).strip()

    if kind == "status-update":
        st = res.get("status") or {}
        state = st.get("state") or "status-update"
        msg = st.get("message") or {}
        text = join_text(msg.get("parts"))
        # f"status: {state}"
        return f"status: {state}\n\n{text}" if text else ""

    if kind == "artifact-update":
        text = join_text((res.get("artifact") or {}).get("parts"))
        # "status: artifact-update"
        return f"status: completed\n\n{text}" if text else ""

    if kind == "task":
        # initial submission event
        state = (res.get("status") or {}).get("state") or "submitted"
        # optionally show last history message text
        hist = res.get("history") or []
        last = hist[-1] if hist else {}
        text = join_text(last.get("parts"))
        return f"status: {state}\n\n{text}" if text else f"status: {state}"

    return None


async def interact_with_server(client: A2AClient) -> None:
    # Let server assign the first context_id on first turn; reuse it afterwards
    last_context_id: str | None = uuid4().hex

    while True:
        user_input = get_user_query()
        if user_input.lower() == "exit":
            print("Thank You for experimenting A2A jira agent")
            break

        print("last_context_id::::", last_context_id)

        send_message_payload: dict[str, Any] = {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": user_input}],
                "message_id": uuid4().hex,
                'metadata': {
                    'max_tokens': 100
                }
            }
        }
        if last_context_id:
            send_message_payload["message"]["context_id"] = last_context_id

        # Show outgoing payload
        try:
            print("Request payload JSON:")
            print(json.dumps(send_message_payload, indent=2, ensure_ascii=False))
        except Exception:
            print(f"Request payload (raw dict): {send_message_payload}")

        try:
            # Build request and start streaming
            message_request = SendStreamingMessageRequest(
                id=uuid4().hex,
                params=MessageSendParams(**send_message_payload),
            )
            print(f"[send] streaming request id={message_request.id}")
            stream_response = client.send_message_streaming(message_request)
            async for chunk in stream_response:
                data = chunk.model_dump(mode='json', exclude_none=True)
                print(data, "\n")
                line = format_stream_event(data)
                if line:
                    print(line)
                print("\n\n")

        except Exception as e:
            print(f"An error occurred: {e}")


async def main() -> None:
    print("Welcome to the A2A client!")
    print("Please enter your query (type 'exit' to quit):")
    headers = {"Authorization": "Bearer satish_token_a2a_2"}
    async with httpx.AsyncClient(timeout=30, headers=headers) as httpx_client:
        card_resolver = A2ACardResolver(httpx_client, "http://localhost:10002")
        card = await card_resolver.get_agent_card()
        print(f"Resolved jira agent card: {card}")
        a2a_client = A2AClient(
            httpx_client, card, url="http://localhost:10002")
        await interact_with_server(a2a_client)


if __name__ == "__main__":
    asyncio.run(main())
