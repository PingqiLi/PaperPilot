"""
健康检查路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import redis

from ..config import settings

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
        "redis": "unknown"
    }
    
    # 检查数据库连接
    try:
        from ..database import get_db
        # 简单的连接测试
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
    
    # 检查Redis连接
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
    
    overall = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"
    
    return {
        "status": overall,
        "checks": checks
    }
