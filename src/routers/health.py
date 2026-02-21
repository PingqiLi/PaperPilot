"""
健康检查路由
"""
from fastapi import APIRouter
from sqlalchemy import text

from ..database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    """基础健康检查"""
    return {"status": "healthy"}


@router.get("/health/detailed")
async def detailed_health_check():
    """详细健康检查"""
    checks = {
        "api": "healthy",
        "database": "unknown",
    }

    # 检查数据库连接
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
        db.close()
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"

    overall = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"

    return {
        "status": overall,
        "checks": checks,
    }
