from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from ai_app.logger.log_config import get_app_logger
from fastapi import APIRouter, HTTPException
import json
# from ai_app.app import app
from strands import Agent, tool
from strands_tools import calculator, current_time, http_request, use_aws
from strands.models import BedrockModel
from strands.models.openai import OpenAIModel
from dotenv import load_dotenv
import os
import asyncio
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from ai_app.logger.thread_local_context import get_txid, set_txid, set_websocket, get_websocket, clear_websocket
from ai_app.llm_models.models import get_model
import traceback

logger = get_app_logger()


agent_webosocket_router_mcp = APIRouter(
    prefix="/atlas-mcp",
    tags=["atlas-websocket-mcp"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8081/atlas-mcp/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        # Use dicts for maps; cache per-connection state
        self.map_agent: dict[WebSocket, Agent] = {}
        self.map_client: dict[str, MCPClient] = {}
        self.map_tools: dict[str, list] = {}
        self.map_ws_txid: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def add_agent(self, websocket: WebSocket, agent):
        self.map_agent[websocket] = agent

    async def add_mcp_client(self, txid: str, mcp_client):
        self.map_client[txid] = mcp_client

    async def get_mcp_client(self, txid: str):
        # return self.map_client[txid]
        return self.map_client.get(txid)

    async def get_agent(self, websocket: WebSocket):
        return self.map_agent[websocket]

    async def set_ws_txid(self, websocket: WebSocket, txid: str):
        self.map_ws_txid[websocket] = txid

    async def set_mcp_tools(self, txid: str, tools: list):
        self.map_tools[txid] = tools

    async def get_mcp_tools(self, txid: str):
        return self.map_tools.get(txid)

    async def disconnect(self, websocket: WebSocket):
        # Remove from active list and agent map
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.map_agent:
            del self.map_agent[websocket]

        # Cleanup any MCP client associated via txid
        txid = self.map_ws_txid.pop(websocket, None)
        if txid:
            client = self.map_client.pop(txid, None)
            # Drop cached tools
            if txid in self.map_tools:
                del self.map_tools[txid]
            # Try to close the client gracefully
            if client is not None:
                try:
                    # Prefer exiting context if we entered with __enter__
                    aexit = getattr(client, "__aexit__", None)
                    if callable(aexit):
                        res = aexit(None, None, None)
                        if asyncio.iscoroutine(res):
                            await res
                    else:
                        xexit = getattr(client, "__exit__", None)
                        if callable(xexit):
                            xexit(None, None, None)
                        else:
                            # Fallback: Support both sync and async close methods
                            close_method = getattr(client, "close", None) or getattr(
                                client, "aclose", None)
                            if callable(close_method):
                                res = close_method()
                                if asyncio.iscoroutine(res):
                                    await res
                except Exception:
                    # Best-effort cleanup
                    pass

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


model = OpenAIModel(
    # client_args={
    #    "api_key": "<KEY>",
    # },
    # **model_config
    model_id="gpt-4-turbo",
    params={
        "max_tokens": 1000,
        "temperature": 0.7,
    }
)


@tool
async def get_weather_jira_appointment_agent(prompt: str) -> str:
    """
    You are a agent who can perform 3 tasks
    weather - you can respond to weather information of a state
    jira - you can respond to jira issues
    appointment - you can create or schedule appointments

    Args:
        prompt (str): The input prompt

    Returns:
        str: Returns either jira or weather or appointment related information based on prompt input
    """
    try:
        print(f"get_txid::::{get_txid()}")
        txid = get_txid()
       # ws = get_websocket()
        mcp_client = await manager.get_mcp_client(txid)
        print(f"mcp_client:::in cache :{mcp_client}")
        if mcp_client:
           # mcp_client = await manager.get_mcp_client(txid)
            print(f"mcp_client:::existing:{mcp_client}")
        else:
            mcp_client = MCPClient(
                lambda: streamablehttp_client(
                    # url="http://localhost:8000/mcp",
                    # url="http://host.docker.internal:8000/mcp",
                    # nginx with 2 mcp servers on 8000, 8001 port
                    url="http://host.docker.internal:8888/mcp",
                    # Get pat token from here: https://github.com/settings/personal-access-tokens

                    headers={"Authorization": f"Bearer {txid}"}
                )
            )
            # Enter the client context ONCE and keep it open for this txid
            try:
                entered_client = mcp_client.__enter__()
                # Some context managers return self; use whichever is returned
                mcp_client = entered_client or mcp_client
            except Exception:
                # If __enter__ is unavailable or fails, client may lazy-init; proceed
                pass
            await manager.add_mcp_client(txid, mcp_client)
            print(f"mcp_client:::new:{mcp_client}")

        # Reuse cached tools if available; otherwise list and cache
        mcp_tools = await manager.get_mcp_tools(txid)
        if not mcp_tools:
            mcp_tools = mcp_client.list_tools_sync()
            await manager.set_mcp_tools(txid, mcp_tools)

        model = await get_model()
        agent = Agent(model=model, tools=mcp_tools, callback_handler=None)
        full_response = ""
        agent_stream = agent.stream_async(prompt)
        async for event in agent_stream:
            if "data" in event:
                # print(event["data"], end="", flush=True)
                chunk = event["data"]
                full_response += chunk
        return full_response if full_response else "No response generated"
    except Exception as e:
        error_msg = f"Error in specialized agent: {str(e)}"
        print(f"\n   ❌ {error_msg}")
        traceback.print_exc()
        tb_str = traceback.format_exc()
        print("Full traceback:")
        print(tb_str)
        return error_msg


async def get_agent():
    model = await get_model()
    return Agent(model=model, tools=[get_weather_jira_appointment_agent], callback_handler=None, system_prompt="you are specialist in getting weather information, jira tickets and creating appointments.")


async def process_streaming_response(agent, message):
    try:

        """1. What is the time right now?
            2. Calculate 3111696 / 74088
            3. Tell me how many letter R's are in the word "strawberry" 🍓
            4. get tickets assisgned for id user123 and show me emailId
            """

        full_response = ""
        agent_stream = agent.stream_async(message)
        async for event in agent_stream:
            if "data" in event:
                chunk = event["data"]
                full_response += chunk
        print(f"agent response::: {full_response}")
        return full_response
    except Exception as e:
        print(f"\n❌ Error during agent response: {e}")


manager = ConnectionManager()


@agent_webosocket_router_mcp.get("/")
async def get():
    return HTMLResponse(html)


@agent_webosocket_router_mcp.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    agent = await get_agent()
    await manager.add_agent(websocket, agent)
    set_txid()
    # Associate this websocket with the generated txid for lifecycle management
    try:
        await manager.set_ws_txid(websocket, get_txid())
    except Exception:
        pass
    set_websocket(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received message from client {client_id}: {data}")

            # Try to parse JSON message from React client
            try:
                agent = await manager.get_agent(websocket)
                message_data = json.loads(data)
                logger.info(f"message_data: {message_data} , agent: {agent}")
                message = message_data.get("message", data)
                message = await process_streaming_response(agent, message)
            except json.JSONDecodeError:
                # Fallback to raw text if not JSON
                message = data
                logger.info(f"message_data exception: {message}")
                message = await process_streaming_response(agent, message)
            except Exception as e:
                logger.info(f"error during reading message : str{e}")
                message = data

            # Send response back to the client
            response = {"message": f"{message}", "client_id": client_id}
            await manager.send_personal_message(json.dumps(response), websocket)

            # Optionally broadcast to all clients
            # await manager.broadcast(f"Client #{client_id} says: {message}")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        logger.info(f"Client #{client_id} disconnected")
       # await manager.broadcast(f"Client #{client_id} left the chat")
    finally:
        clear_websocket()
