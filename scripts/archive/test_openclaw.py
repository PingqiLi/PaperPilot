
import asyncio
import logging
import sys
import os

# Add src to python path to import OpenClawClient
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.services.openclaw_client import OpenClawClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    print("Testing OpenClaw connection (Dev Gateway with Token)...")
    client = OpenClawClient(uri="ws://127.0.0.1:19001", token="testtoken")
    
    try:
        await client.connect()
        print("✅ Connected successfully!")
        
        # In dev mode with auth=none, we might not need complex handshake, 
        # but let's try a simple agent task.
        print("Testing agent execution (echo)...")
        task = "Please reply with 'OpenClaw is online'."
        # Dev gateway usually has a 'main' agent or we can target any available agent.
        # Let's try 'dev' first.
        response = await client.send_agent_task(task, agent_id="dev")
        
        print(f"Agent Response: {response}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
