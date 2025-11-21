from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from ai_app.logger.log_config import get_app_logger
from fastapi import APIRouter
import json
from dotenv import load_dotenv
import os
import asyncio
from strands.tools.mcp.mcp_client import MCPClient
from ai_app.logger.thread_local_context import get_txid, clear_txid, set_websocket, get_websocket, clear_websocket, set_transaction_id
import traceback
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


logger = get_app_logger()


facade_websocket = APIRouter(
    prefix="/ai-agent",
    tags=["ai-agent"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def set_ws_txid(self, websocket: WebSocket, txid: str):
        pass

    async def disconnect(self, websocket: WebSocket):
        # Remove from active list and agent map
        if websocket in self.active_connections:
            try:
                await websocket.close(code=1000, reason="")
            except Exception:
                pass
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)


manager = ConnectionManager()


@facade_websocket.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    try:
        await manager.connect(websocket)
        set_transaction_id(client_id)
        try:
            await manager.set_ws_txid(websocket, get_txid())
        except Exception:
            pass
        set_websocket(websocket)
        headers = {"Authorization": f"Bearer {client_id}"}
        async with httpx.AsyncClient(timeout=30, headers=headers) as httpx_client:
            card_resolver = A2ACardResolver(
                httpx_client, "http://localhost:10003")
            card = await card_resolver.get_agent_card()
            print(f"Resolved jira agent card: {card}")
            a2a_client = A2AClient(
                httpx_client, card, url="http://localhost:10003")
            await interact_with_server(a2a_client, websocket, client_id)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        logger.info(f"Client #{client_id} disconnected")
    except Exception as e:
        print(
            f"Error during processing websocket for client_id:: {client_id} {e}")
    finally:
        clear_websocket()
        clear_txid()


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


async def interact_with_server(client: A2AClient, websocket: WebSocket, client_id: str) -> None:
    # Let server assign the first context_id on first turn; reuse it afterwards
    last_context_id: str | None = uuid4().hex

    while True:
        user_input = await websocket.receive_text()
        logger.info(f"Received message from client {client_id}: {user_input}")

        print("last_context_id::::", last_context_id)

        try:
            message_data = json.loads(user_input)
            logger.info(f"message_data: {message_data}")
            user_input = message_data.get("message", user_input)
        except json.JSONDecodeError:
            # Fallback to raw text if not JSON
            logger.info(f"message_data exception: {user_input}")
        except Exception as e:
            logger.info(
                f"error during reading message : {user_input} .... {e}")

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
                    response = {"message": f"{line}", "client_id": client_id}
                    await manager.send_personal_message(json.dumps(response), websocket)
                print("\n\n")

        except Exception as e:
            print(f"An error occurred: {e}")
            response = {"message": f"{e}", "client_id": client_id}
            await manager.send_personal_message(json.dumps(response), websocket)
