
import asyncio
import sys
import structlog
from datetime import datetime
try:
    from termcolor import colored
except ImportError:
    def colored(text, color=None, on_color=None, attrs=None):
        return text

# Setup paths
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.services.semantic_scholar import semantic_scholar
from src.services.two_stage_filter import TwoStageFilter
from src.models import Paper

logger = structlog.get_logger(__name__)
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/paper_agent"

# Instantiate service
two_stage_filter = TwoStageFilter()

logger = structlog.get_logger(__name__)
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/paper_agent"

# Live Verification - using real TwoStageFilter and OpenClawClient
# Ensure OpenClaw Gateway is running on ws://127.0.0.1:18789


# Test Configuration
TEST_TOPIC = {
    "name": "LLM Inference Optimization",
    "semantic_query": "Large Language Model inference optimization techniques",
    "topic_description": """
    关注大语言模型(LLM)的推理加速技术。
    核心关注点：
    1. 投机采样 (Speculative Decoding)
    2. KV Cache 优化 (如 PagedAttention)
    3. 量化技术 (Quantization) 在推理中的应用
    4. 模型剪枝与蒸馏
    
    不关注：
    1. 纯模型训练 (Pre-training)
    2. 通用的NLP综述
    3. 提示工程 (Prompt Engineering)
    """
}

async def verify_rapid_screening():
    print(colored("\n🚀 Starting User Screening Verification (Local Agent)", "green", attrs=["bold"]))
    print(f"Topic: {TEST_TOPIC['name']}")
    print(f"Query: {TEST_TOPIC['semantic_query']}")
    print("-" * 50)

    # 1. S2 Search
    # 1. S2 Search
    print(f"\n📡 Step 1: Searching Semantic Scholar...")
    papers_data = await semantic_scholar.search_papers(
        query=TEST_TOPIC["semantic_query"],
        limit=1,
        year_start=2023
    )
    
    if not papers_data:
        print("❌ No papers found from S2.")
        return

    print(f"✅ Found {len(papers_data)} papers from S2.")

    # 2. Agent Scoring
    print(f"\n🧠 Step 2: Agent Semantic Scoring (using Topic Description)...")
    print(f"Description Length: {len(TEST_TOPIC['topic_description'])} chars")
    
    scored_papers = []
    
    for i, p_data in enumerate(papers_data):
        # Convert S2 data to Paper model (in-memory)
        # S2 fields: paperId, title, abstract, citationCount, year, etc.
        paper = Paper(
            title=p_data.get("title"),
            abstract=p_data.get("abstract"),
            arxiv_id=p_data.get("externalIds", {}).get("ArXiv", f"s2:{p_data.get('paperId')}"),
            citation_count=p_data.get("citationCount", 0),
            published_date=datetime.utcnow() # Mock date
        )
        
        if not paper.abstract:
            print(f"⚠️ Skipping Paper {i+1}: {paper.title[:50]}... (No Abstract)")
            continue

        print(f"Evaluating Paper {i+1}: {paper.title[:50]}...")
        
        # Call TwoStageFilter with topic_description
        result = await two_stage_filter.stage2_semantic_scoring(
            paper, 
            TEST_TOPIC["topic_description"]
        )
        
        score = result["score"]
        reason = result["reason"]
        
        print(f"  -> Score: {score}/10")
        print(f"  -> Reason: {reason}")
        
        if score >= 6:
            scored_papers.append({
                "title": paper.title,
                "score": score,
                "reason": reason,
                "citations": paper.citation_count
            })

    # 3. Results
    print(f"\n" + "="*50)
    print(f"🏆 Verification Results: {len(scored_papers)}/{len(papers_data)} passed threshold (>=6)")
    print("="*50)
    
    for p in scored_papers:
        print(f"[{p['score']}] {p['title']} (Citations: {p['citations']})")
        print(f"Reason: {p['reason']}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(verify_rapid_screening())
