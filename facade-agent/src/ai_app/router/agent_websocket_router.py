from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from ai_app.logger.log_config import get_app_logger
from fastapi import APIRouter, HTTPException
import json
# from ai_app.app import app

logger = get_app_logger()


agent_webosocket_router = APIRouter(
    prefix="/atlas",
    tags=["atlas-websocket"],
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
            var ws = new WebSocket(`ws://localhost:8081/atlas/ws/${client_id}`);
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

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@agent_webosocket_router.get("/")
async def get():
    return HTMLResponse(html)


@agent_webosocket_router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received message from client {client_id}: {data}")

            # Try to parse JSON message from React client
            try:
                message_data = json.loads(data)
                message = message_data.get("message", data)
            except json.JSONDecodeError:
                # Fallback to raw text if not JSON
                message = data

            # Send response back to the client
            response = {"message": f"Echo: {message}", "client_id": client_id}
            await manager.send_personal_message(json.dumps(response), websocket)

            # Optionally broadcast to all clients
            # await manager.broadcast(f"Client #{client_id} says: {message}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"Client #{client_id} disconnected")
        await manager.broadcast(f"Client #{client_id} left the chat")
