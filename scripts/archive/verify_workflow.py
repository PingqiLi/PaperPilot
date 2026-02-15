
"""
Verify OpenClaw Workflows
"""
import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings
from src.services.openclaw_service import openclaw_client
from src.workflows.rating import RatingWorkflow
from src.workflows.summarization import SummarizationWorkflow
from src.services.two_stage_filter import two_stage_filter

async def test_rating():
    print("\n--- Testing RatingWorkflow ---")
    workflow = RatingWorkflow(openclaw_client)
    
    title = "Attention Is All You Need"
    abstract = "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely."
    interests = "Deep Learning, NLP, Transformer architectures"
    
    print(f"Rating paper: {title}")
    result = await workflow.run(title, abstract, interests)
    print(f"Result: {result}")
    return result

async def test_summarization():
    print("\n--- Testing SummarizationWorkflow ---")
    workflow = SummarizationWorkflow(openclaw_client)
    
    content = """
    The Transformer is the first transduction model relying entirely on self-attention to compute representations of its input and output without using sequence-aligned RNNs or convolution. In the following sections, we will describe the Transformer, motivate self-attention and discuss its advantages over [17, 18] and [9].
    
    Model Architecture
    Most competitive neural sequence transduction models have an encoder-decoder structure [5, 2, 35]. Here, the encoder maps an input sequence of symbol representations (x1, ..., xn) to a sequence of continuous representations z = (z1, ..., zn). Given z, the decoder then generates an output sequence (y1, ..., ym) of symbols one element at a time. At each step the model is auto-regressive [10], consuming the previously generated symbols as additional input when generating the next.
    """
    
    print(f"Summarizing content (len={len(content)})...")
    result = await workflow.run(content)
    print(f"Result: {result}")
    return result

async def test_filter_expansion():
    print("\n--- Testing TwoStageFilter Expansion ---")
    query = "Large Language Model Agents"
    print(f"Expanding query: {query}")
    keywords = await two_stage_filter.expand_keywords(query)
    print(f"Keywords: {keywords}")
    return keywords

async def main():
    # Ensure token is set (from previous steps we know it might be needed, but config handles it)
    print(f"Connecting to OpenClaw at {settings.openclaw_gateway_uri}...")
    
    # Run tests
    try:
        await test_rating()
        await test_summarization()
        await test_filter_expansion()
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        # Close client if needed (it's a singleton, usually persists, but for script clean exit)
        if openclaw_client.ws:
            await openclaw_client.ws.close()

if __name__ == "__main__":
    asyncio.run(main())
