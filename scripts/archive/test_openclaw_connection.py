import asyncio
import websockets
import json
import uuid

async def test_connection():
    uri = "ws://127.0.0.1:18789"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # Send a handshake/ping
            # Based on OpenClaw protocol, we might need a specific handshake or just listen
            # But just connecting proves the port is open and accepting WS.
            
            # Try to send a simple request if possible, or just exit
            print("Connection successful. Closing.")
            return True
    except ConnectionRefusedError:
        print("Connection refused. Service is likely not running.")
        return False
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    if not success:
        exit(1)
