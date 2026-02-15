import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.semantic_scholar import semantic_scholar
from src.config import settings, rules_config

async def verify():
    print(f"Checking S2 Configuration...")
    print(f"Settings Key: {'***' if settings.s2_api_key else 'None'}")
    print(f"Rules config Key: {'***' if rules_config.s2_api_key else 'None'}")
    print(f"Effective Key: {'***' if semantic_scholar.api_key else 'None'}")
    print(f"Rate Limit Delay: {semantic_scholar.rate_limit_delay}s")
    
    if not semantic_scholar.api_key:
        print("❌ No API Key found. Rate limits will be strict (1 RPS).")
        print("Please enable the key in .env or via Global Settings UI.")
    else:
        print("✅ API Key found. High rate limits enabled.")
        
    print("\nExecuting Test Request (GET Paper)...")
    # Test paper: GPTQ (arXiv:2210.17323)
    try:
        res = await semantic_scholar.get_paper_by_arxiv_id("2210.17323")
        
        if res:
            print(f"✅ Success! Found paper: {res.get('semantic_scholar_id')}")
            print(f"Title: {res.get('title')}") # get_paper_by_arxiv_id doesn't return title in dict currently, let's see. 
            # Ah, the current service implementation only returns paperId, citationCount.
            print(f"Citations: {res.get('citation_count')}")
        else:
            print("❌ Request Failed: Paper not found or API error.")
    except Exception as e:
        print(f"❌ Exception occurred: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
