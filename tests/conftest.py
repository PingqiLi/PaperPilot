"""
pytest fixtures
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_paper_data():
    """示例论文数据"""
    return {
        "arxiv_id": "2412.12345",
        "title": "Efficient INT4 Quantization for Large Language Models",
        "authors": ["Alice Smith", "Bob Johnson"],
        "abstract": "We propose a novel INT4 quantization method to accelerate LLM inference.",
        "categories": ["cs.AI", "cs.LG"],
        "pdf_url": "https://arxiv.org/pdf/2412.12345.pdf"
    }


@pytest.fixture
def user_interests():
    """用户兴趣描述"""
    return "大模型推理优化、量化压缩、注意力机制改进"


@pytest.fixture
def rules_config_data():
    """示例规则配置"""
    return {
        "categories": ["cs.AI", "cs.LG", "cs.CL"],
        "keywords": {
            "include": ["transformer", "quantization", "LLM"],
            "exclude": ["survey", "review"]
        },
        "interests": "大模型推理优化、量化压缩",
        "date_range": 7
    }
