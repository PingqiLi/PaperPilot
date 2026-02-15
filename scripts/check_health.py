
import asyncio
import sys
import os
import structlog
from sqlalchemy import text
try:
    from termcolor import colored
except ImportError:
    def colored(text, color=None, on_color=None, attrs=None):
        return text

# Setup paths
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.database import SessionLocal
from src.services.semantic_scholar import semantic_scholar
from src.services.openclaw_client import OpenClawClient
from src.config import settings

logger = structlog.get_logger(__name__)

def check_database():
    print(colored("\n🛠️ Checking Database Connection...", "cyan"))
    try:
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        session.close()
        print(colored("✅ Database connection successful.", "green"))
        return True
    except Exception as e:
        print(colored(f"❌ Database connection failed: {e}", "red"))
        return False

async def check_semantic_scholar():
    print(colored("\n📚 Checking Semantic Scholar API...", "cyan"))
    try:
        # Simple search to verify API key and connectivity
        papers = await semantic_scholar.search_papers(query="Large Language Models", limit=1)
        if papers and len(papers) > 0:
            print(colored(f"✅ S2 API working (Found paper: {papers[0]['title'][:30]}...)", "green"))
            return True
        else:
            print(colored("⚠️ S2 API returned no results (Check verify_s2.py for details).", "yellow"))
            return False
    except Exception as e:
        print(colored(f"❌ S2 API check failed: {e}", "red"))
        return False

async def check_openclaw():
    print(colored("\n🤖 Checking OpenClaw Gateway...", "cyan"))
    client = OpenClawClient(token=settings.openclaw_gateway_token)
    try:
        await client.connect()
        print(colored(f"✅ OpenClaw Gateway connected at {settings.openclaw_gateway_uri}", "green"))
        
        # Optional: Send a ping or simple request if supported, 
        # but connection is usually sufficient for health check.
        await client.close()
        return True
    except Exception as e:
        print(colored(f"❌ OpenClaw Gateway connection failed: {e}", "red"))
        print(colored("   Tip: Ensure gateway is running on port 18789.", "yellow"))
        return False

async def main():
    print(colored("🏥 Starting System Health Check...", "white", attrs=["bold"]))
    
    results = {
        "Database": check_database(),
        "Semantic Scholar": await check_semantic_scholar(),
        "OpenClaw Agent": await check_openclaw()
    }
    
    print(colored("\n📊 Summary:", "white", attrs=["bold"]))
    all_passed = True
    for component, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        color = "green" if passed else "red"
        print(colored(f"{component}: {status}", color))
        if not passed:
            all_passed = False
            
    if all_passed:
        print(colored("\n🚀 System is READY for deployment!", "green", attrs=["bold"]))
        print(colored("💡 To verify end-to-end agent workflow, run: python scripts/run_screening_test.py", "blue"))
        sys.exit(0)
    else:
        print(colored("\n⚠️ System has issues. Please fix failures above.", "red", attrs=["bold"]))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
