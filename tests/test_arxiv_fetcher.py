"""
ArXiv抓取服务单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.services.arxiv_fetcher import ArxivFetcher


class TestArxivFetcher:
    """ArxivFetcher 测试类"""

    def test_build_query_single_category(self):
        """测试单分类查询构建"""
        fetcher = ArxivFetcher()
        query = fetcher.build_query(categories=["cs.AI"])
        
        assert "cat:cs.AI" in query

    def test_build_query_multiple_categories(self):
        """测试多分类查询构建"""
        fetcher = ArxivFetcher()
        query = fetcher.build_query(categories=["cs.AI", "cs.LG", "cs.CL"])
        
        assert "cat:cs.AI" in query
        assert "cat:cs.LG" in query
        assert "cat:cs.CL" in query
        assert " OR " in query

    def test_build_query_with_include_keywords(self):
        """测试包含关键词查询"""
        fetcher = ArxivFetcher()
        query = fetcher.build_query(
            categories=["cs.AI"],
            keywords_include=["transformer", "quantization"]
        )
        
        assert '"transformer"' in query
        assert '"quantization"' in query

    def test_build_query_with_exclude_keywords(self):
        """测试排除关键词查询"""
        fetcher = ArxivFetcher()
        query = fetcher.build_query(
            categories=["cs.AI"],
            keywords_exclude=["survey", "review"]
        )
        
        assert 'NOT "survey"' in query
        assert 'NOT "review"' in query

    def test_filter_by_keywords_include(self):
        """测试本地关键词包含过滤"""
        fetcher = ArxivFetcher()
        
        papers = [
            {"title": "Transformer Optimization", "abstract": "A study on transformers"},
            {"title": "Image Classification", "abstract": "Using CNN for images"},
            {"title": "LLM Quantization", "abstract": "INT4 quantization method"}
        ]
        
        filtered = fetcher.filter_by_keywords(
            papers,
            keywords_include=["transformer", "quantization"],
            keywords_exclude=[]
        )
        
        assert len(filtered) == 2
        assert filtered[0]["title"] == "Transformer Optimization"
        assert filtered[1]["title"] == "LLM Quantization"

    def test_filter_by_keywords_exclude(self):
        """测试本地关键词排除过滤"""
        fetcher = ArxivFetcher()
        
        papers = [
            {"title": "Transformer Survey", "abstract": "A comprehensive survey"},
            {"title": "LLM Optimization", "abstract": "Novel optimization method"},
        ]
        
        filtered = fetcher.filter_by_keywords(
            papers,
            keywords_include=[],
            keywords_exclude=["survey"]
        )
        
        assert len(filtered) == 1
        assert filtered[0]["title"] == "LLM Optimization"

    def test_filter_by_keywords_empty(self):
        """测试无关键词时返回全部"""
        fetcher = ArxivFetcher()
        
        papers = [
            {"title": "Paper 1", "abstract": "Content 1"},
            {"title": "Paper 2", "abstract": "Content 2"},
        ]
        
        filtered = fetcher.filter_by_keywords(papers, [], [])
        
        assert len(filtered) == 2

    @pytest.mark.asyncio
    async def test_fetch_integration(self):
        """集成测试：实际调用ArXiv API"""
        fetcher = ArxivFetcher()
        
        # 抓取少量论文进行验证
        papers = fetcher.fetch(
            categories=["cs.AI"],
            max_results=3,
            date_range=30
        )
        
        # 验证返回结构
        assert isinstance(papers, list)
        if papers:  # 可能没有结果
            paper = papers[0]
            assert "arxiv_id" in paper
            assert "title" in paper
            assert "authors" in paper
            assert "abstract" in paper
            assert "categories" in paper
            assert "pdf_url" in paper
