from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import TokenUsage
from ..services import app_settings

router = APIRouter(tags=["stats"])


@router.get("/costs", response_model=Dict[str, Any])
def get_cost_stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    start_of_day = datetime(now.year, now.month, now.day)

    today_row = db.query(
        func.sum(TokenUsage.cost_yuan).label("cost"),
        func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens).label("tokens"),
    ).filter(TokenUsage.timestamp >= start_of_day).first()

    total_row = db.query(
        func.sum(TokenUsage.cost_yuan).label("cost"),
        func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens).label("tokens"),
    ).first()

    start_of_month = datetime(now.year, now.month, 1)
    month_row = db.query(
        func.sum(TokenUsage.cost_yuan).label("cost"),
    ).filter(TokenUsage.timestamp >= start_of_month).first()

    monthly_cost = float(month_row.cost or 0) if month_row else 0.0
    monthly_budget = app_settings.get_float("monthly_budget_cap")

    return {
        "today_cost": float(today_row.cost or 0) if today_row else 0.0,
        "today_tokens": int(today_row.tokens or 0) if today_row else 0,
        "total_cost": float(total_row.cost or 0) if total_row else 0.0,
        "total_tokens": int(total_row.tokens or 0) if total_row else 0,
        "monthly_cost": monthly_cost,
        "monthly_budget": monthly_budget,
        "budget_usage_pct": round(monthly_cost / monthly_budget * 100, 1) if monthly_budget > 0 else 0,
        "currency": "CNY",
    }


@router.get("/costs/daily", response_model=List[Dict[str, Any]])
def get_daily_costs(
    days: int = Query(default=10, ge=1, le=90),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    date_col = func.date(TokenUsage.timestamp)

    rows = (
        db.query(
            date_col.label("date"),
            TokenUsage.model,
            func.sum(TokenUsage.cost_yuan).label("cost"),
            func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens).label("tokens"),
            func.count().label("requests"),
        )
        .filter(TokenUsage.timestamp >= since)
        .group_by(date_col, TokenUsage.model)
        .order_by(date_col)
        .all()
    )

    return [
        {
            "date": str(r.date),
            "model": r.model or "unknown",
            "cost": float(r.cost or 0),
            "tokens": int(r.tokens or 0),
            "requests": r.requests,
        }
        for r in rows
    ]


@router.get("/costs/requests", response_model=Dict[str, Any])
def get_request_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)

    query = db.query(TokenUsage).filter(TokenUsage.timestamp >= since)
    total = query.count()

    items = (
        query.order_by(TokenUsage.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "timestamp": item.timestamp.isoformat() if item.timestamp else None,
                "model": item.model or "unknown",
                "workflow": item.workflow or "—",
                "input_tokens": item.input_tokens,
                "output_tokens": item.output_tokens,
                "tokens": (item.input_tokens or 0) + (item.output_tokens or 0),
                "cost": float(item.cost_yuan or 0),
            }
            for item in items
        ],
    }
