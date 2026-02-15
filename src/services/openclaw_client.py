
import asyncio
import json
import logging
import uuid
import websockets
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class OpenClawClient:
    """
    Client for interacting with OpenClaw Gateway via WebSocket.
    Implements a JSON-RPC style protocol to send tasks to agents.
    """
    
    def __init__(self, uri: str = "ws://127.0.0.1:18789", token: Optional[str] = None):
        self.uri = uri
        self.token = token
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._connected = False

    async def connect(self):
        """Establish WebSocket connection and start listener loop."""
        if self._connected:
            return

        try:
            extra_headers = {}
            if self.token:
                extra_headers["Authorization"] = f"Bearer {self.token}"
            
            self.ws = await websockets.connect(self.uri, additional_headers=extra_headers)
            self._connected = True
            logger.info(f"Connected to OpenClaw Gateway at {self.uri}")
            
            # Start background listener
            self._listener_task = asyncio.create_task(self._listen())
            
            # Send initial hello/connect request
            await self._send_connect_handshake()
            
        except Exception as e:
            logger.error(f"Failed to connect to OpenClaw: {e}")
            self._connected = False
            raise

    async def close(self):
        """Close the connection."""
        if self.ws:
            await self.ws.close()
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        self._connected = False
        logger.info("OpenClaw connection closed")

    async def _listen(self):
        """Background loop to receive messages."""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
            self._connected = False
        except Exception as e:
            logger.error(f"Listener loop error: {e}")
            self._connected = False

    async def _handle_message(self, data: Dict[str, Any]):
        """Dispatch incoming message to waiting requests."""
        # Check if it's a response to a request
        msg_id = data.get("id")
        if msg_id and msg_id in self._pending_requests:
            future = self._pending_requests[msg_id]
            
            # Protocol: { type: "res", id: "...", ok: boolean, payload: ... }
            if data.get("type") == "res":
                if data.get("ok"):
                    payload = data.get("payload", {})
                    # Check if this is just an acknowledgement
                    is_accepted = payload.get("status") == "accepted"
                    
                    # If we expect a final response and this is just 'accepted', keep waiting
                    if getattr(future, "expect_final", False) and is_accepted:
                        return

                    if not future.done():
                        future.set_result(payload)
                else:
                    error_msg = data.get("error", {}).get("message", "Unknown error")
                    if not future.done():
                        future.set_exception(Exception(error_msg))
            # Handle other types if necessary (events)

    async def request(self, method: str, params: Dict[str, Any], timeout: float = 30.0, expect_final: bool = False) -> Any:
        """Send a JSON-RPC request and await response."""
        if not self._connected:
            await self.connect()

        req_id = str(uuid.uuid4())
        frame = {
            "type": "req",
            "id": req_id,
            "method": method,
            "params": params
        }

        future = asyncio.get_running_loop().create_future()
        # Tag the future with expect_final flag
        setattr(future, "expect_final", expect_final)
        self._pending_requests[req_id] = future

        try:
            await self.ws.send(json.dumps(frame))
            return await asyncio.wait_for(future, timeout)
        finally:
            self._pending_requests.pop(req_id, None)

    async def _send_connect_handshake(self):
        """
        Send the initial 'connect' handshake required by Gateway.
        Based on src/gateway/client.ts structure.
        """
        # Minimal connect params
        params = {
            "client": {
                "id": "gateway-client", 
                "version": "0.1.0",
                "mode": "backend",
                "platform": "darwin"
            },
            "minProtocol": 3,
            "maxProtocol": 3,
            "caps": [],
            "role": "operator",
            "scopes": ["operator.admin"]
        }
        
        if self.token:
            params["auth"] = {"token": self.token}
        
        # We expect a HelloOk response
        response = await self.request("connect", params, timeout=5.0)
        logger.info(f"Handshake successful: {response}")

    async def send_agent_task(
        self, 
        task: str, 
        agent_id: str = "main", 
        system_prompt: Optional[str] = None,
        wait: bool = True
    ) -> Dict[str, Any]:
        """
        Send a task to an agent via the 'agent' method.
        Matches `agentViaGatewayCommand` logic.
        """
        params = {
            "message": task,
            "agentId": agent_id,
            "deliver": False, 
            "channel": "webchat", 
            "timeout": 600, 
            "idempotencyKey": str(uuid.uuid4())
        }
        
        if system_prompt:
            params["extraSystemPrompt"] = system_prompt

        response = await self.request("agent", params, timeout=600, expect_final=wait)
        return response

# Usage Example:
# client = OpenClawClient()
# await client.connect()
# res = await client.send_agent_task("Hello world")
# print(res)
# await client.close()
