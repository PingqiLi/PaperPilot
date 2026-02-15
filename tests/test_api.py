"""
API路由集成测试
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestHealthRouter:
    """健康检查路由测试"""

    def test_health_check(self, client):
        """测试基础健康检查"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self, client):
        """测试根路径"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        # 修正：检查实际返回的字段
        assert "name" in data
        assert "Paper Agent" in data["name"]


class TestRulesRouter:
    """规则配置路由测试"""

    def test_get_rules(self, client):
        """测试获取规则配置"""
        response = client.get("/api/v1/rules")
        
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data

    def test_get_categories(self, client):
        """测试获取ArXiv分类"""
        response = client.get("/api/v1/rules/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert "cs" in data
        assert "cs.AI" in data["cs"]


class TestPapersRouter:
    """论文路由测试（需要数据库）"""

    @pytest.mark.skip(reason="需要PostgreSQL数据库连接")
    def test_list_papers_empty(self, client):
        """测试空论文列表"""
        response = client.get("/api/v1/papers")
        assert response.status_code == 200

    @pytest.mark.skip(reason="需要PostgreSQL数据库连接")
    def test_paper_status(self, client):
        """测试抓取状态"""
        response = client.get("/api/v1/papers/status")
        assert response.status_code == 200

