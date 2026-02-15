import asyncio
import sys
from pathlib import Path
import httpx
import time

sys.path.append(str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8000/api/v1"

async def test_e2e():
    print("🚀 Starting E2E Test...")
    
    async with httpx.AsyncClient() as client:
        # 1. Create a test ruleset
        print("1️⃣  Creating Test RuleSet...")
        ruleset_data = {
            "name": f"Test-S2-Integration-{int(time.time())}",
            "categories": ["cs.CL"],
            "keywords_include": ["Large Language Model", "Reasoning"],
            "semantic_query": "Large Language Model Reasoning Capabilities",
            "date_range_days": 1095  # 3 years
        }
        res = await client.post(f"{BASE_URL}/rulesets", json=ruleset_data)
        if res.status_code != 200:
            print(f"❌ Failed to create ruleset: {res.text}")
            return
        
        ruleset = res.json()
        rid = ruleset["id"]
        print(f"✅ RuleSet Created: ID={rid}, Name={ruleset['name']}")
        
        # 2. Trigger Collect (S2 Priority)
        print("2️⃣  Triggering Collect (S2 Priority)...")
        res = await client.post(f"{BASE_URL}/rulesets/{rid}/collect")
        if res.status_code != 200:
            print(f"❌ Failed to trigger collect: {res.text}")
            return
        print(f"✅ Collect Triggered: {res.json()['message']}")
        
        # 3. Poll for results
        print("3️⃣  Polling for results (timeout 60s)...")
        start_time = time.time()
        while time.time() - start_time < 60:
            res = await client.get(f"{BASE_URL}/rulesets/{rid}/stats")
            stats = res.json()
            total = stats["total_papers"]
            
            # Also check detailed papers to see citations
            res_papers = await client.get(f"{BASE_URL}/rulesets/{rid}/papers?sort_by=citation_count")
            papers = res_papers.json()["items"]
            
            print(f"   Stats: {total} papers. Top paper citations: {papers[0]['citation_count'] if papers else 'N/A'}")
            
            if total > 0:
                print(f"✅ Success! Collected {total} papers.")
                print(f"🏆 Top Paper: {papers[0]['title']} (Citations: {papers[0]['citation_count']})")
                break
            
            await asyncio.sleep(2)
        else:
            print("❌ Timeout waiting for papers.")

if __name__ == "__main__":
    asyncio.run(test_e2e())
