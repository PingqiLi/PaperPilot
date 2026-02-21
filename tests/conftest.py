import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_paper_data():
    return {
        "arxiv_id": "2412.12345",
        "title": "Efficient INT4 Quantization for Large Language Models",
        "authors": ["Alice Smith", "Bob Johnson"],
        "abstract": "We propose a novel INT4 quantization method to accelerate LLM inference.",
        "categories": ["cs.AI", "cs.LG"],
        "pdf_url": "https://arxiv.org/pdf/2412.12345.pdf",
    }


@pytest.fixture
def sample_s2_paper():
    return {
        "paperId": "abc123",
        "externalIds": {"ArXiv": "2412.12345"},
        "title": "Efficient INT4 Quantization for Large Language Models",
        "abstract": "We propose a novel INT4 quantization method.",
        "authors": [{"name": "Alice Smith"}, {"name": "Bob Johnson"}],
        "year": 2024,
        "citationCount": 150,
        "influentialCitationCount": 25,
        "venue": "NeurIPS",
        "publicationDate": "2024-06-15",
        "publicationTypes": ["JournalArticle"],
        "publicationVenue": {"name": "NeurIPS"},
    }


@pytest.fixture
def sample_ruleset_data():
    return {
        "name": "LLM Inference",
        "topic_sentence": "Efficient inference for large language models including quantization and pruning",
        "categories": ["cs.AI", "cs.LG"],
        "keywords_include": ["quantization", "pruning", "inference"],
        "keywords_exclude": ["survey"],
        "search_queries": ["LLM inference optimization", "neural network quantization"],
    }
