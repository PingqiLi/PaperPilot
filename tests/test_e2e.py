"""
端到端测试 - 需要数据库连接
使用pytest标记：pytest -m e2e 运行
"""
import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 设置测试数据库URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://paper_agent:paper_agent@localhost:5432/paper_agent"
)


def check_database_connection():
    """检查数据库是否可连接"""
    try:
        engine = create_engine(TEST_DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# 如果数据库不可用，跳过所有测试
pytestmark = pytest.mark.skipif(
    not check_database_connection(),
    reason="PostgreSQL数据库不可用"
)


@pytest.fixture(scope="module")
def db_engine():
    """创建测试数据库引擎"""
    engine = create_engine(TEST_DATABASE_URL)
    
    # 创建表
    from src.models.paper import Base
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # 清理：删除所有表
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    """创建数据库会话"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_client(db_engine):
    """创建测试客户端（使用真实数据库）"""
    # 重写数据库依赖
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    
    from src.main import app
    return TestClient(app)


class TestDatabaseOperations:
    """数据库操作测试"""

    def test_create_paper(self, db_session):
        """测试创建论文记录"""
        from src.models.paper import Paper
        
        paper = Paper(
            arxiv_id="2412.99999",
            title="Test Paper for E2E",
            authors=["Test Author"],
            abstract="This is a test abstract.",
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2412.99999.pdf",
            published_date=None
        )
        
        db_session.add(paper)
        db_session.commit()
        
        # 验证
        saved = db_session.query(Paper).filter_by(arxiv_id="2412.99999").first()
        assert saved is not None
        assert saved.title == "Test Paper for E2E"
        
        # 清理
        db_session.delete(saved)
        db_session.commit()

    def test_update_paper_score(self, db_session):
        """测试更新论文评分"""
        from src.models.paper import Paper
        
        paper = Paper(
            arxiv_id="2412.88888",
            title="Test Update Score",
            authors=[],
            abstract="Test",
            categories=["cs.LG"],
            pdf_url="https://arxiv.org/pdf/2412.88888.pdf"
        )
        
        db_session.add(paper)
        db_session.commit()
        
        # 更新评分
        paper.relevance_score = 8
        paper.rating_reason = "高度相关"
        db_session.commit()
        
        # 验证
        updated = db_session.query(Paper).filter_by(arxiv_id="2412.88888").first()
        assert updated.relevance_score == 8
        assert updated.rating_reason == "高度相关"
        
        # 清理
        db_session.delete(updated)
        db_session.commit()


class TestAPIWithDatabase:
    """API端到端测试（真实数据库）"""

    def test_health_with_db(self, test_client):
        """测试健康检查（包含数据库连接）"""
        response = test_client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "connected"

    def test_list_papers_empty(self, test_client, db_session):
        """测试空论文列表"""
        # 清空表
        from src.models.paper import Paper
        db_session.query(Paper).delete()
        db_session.commit()
        
        response = test_client.get("/api/v1/papers")
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_fetch_and_list_papers(self, test_client, db_session):
        """测试抓取并列出论文"""
        from src.models.paper import Paper
        
        # 先添加一条测试数据
        paper = Paper(
            arxiv_id="2412.77777",
            title="E2E Test Paper",
            authors=["E2E Author"],
            abstract="E2E test abstract",
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2412.77777.pdf",
            relevance_score=7
        )
        db_session.add(paper)
        db_session.commit()
        
        # 查询
        response = test_client.get("/api/v1/papers")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        
        # 验证包含我们的测试论文
        arxiv_ids = [p["arxiv_id"] for p in data["items"]]
        assert "2412.77777" in arxiv_ids
        
        # 清理
        db_session.query(Paper).filter_by(arxiv_id="2412.77777").delete()
        db_session.commit()


class TestFetchWorkflow:
    """抓取工作流端到端测试"""

    @pytest.mark.slow
    def test_arxiv_fetch_real(self, db_session):
        """真实ArXiv抓取测试（较慢）"""
        from src.services.arxiv_fetcher import ArxivFetcher
        from src.models.paper import Paper
        
        fetcher = ArxivFetcher()
        
        # 抓取少量论文
        papers = fetcher.fetch(
            categories=["cs.AI"],
            max_results=2,
            date_range=30
        )
        
        assert len(papers) >= 1
        
        # 存入数据库
        for p in papers[:1]:  # 只存一篇
            existing = db_session.query(Paper).filter_by(arxiv_id=p["arxiv_id"]).first()
            if not existing:
                paper = Paper(
                    arxiv_id=p["arxiv_id"],
                    title=p["title"],
                    authors=p["authors"],
                    abstract=p["abstract"],
                    categories=p["categories"],
                    pdf_url=p["pdf_url"]
                )
                db_session.add(paper)
        
        db_session.commit()
        
        # 验证
        count = db_session.query(Paper).count()
        assert count >= 1
