"""
数据库连接管理 - SQLite
"""
import json
from contextlib import contextmanager

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker

from .config import settings
from .models.paper import Base

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _migrate_add_columns():
    """增量迁移：给已有表添加新列（SQLite不支持ALTER TABLE IF NOT EXISTS）"""
    insp = inspect(engine)
    migrations = [
        ("papers", "is_survey", "BOOLEAN DEFAULT 0"),
        ("rulesets", "source_filter", "VARCHAR(20) DEFAULT 'all'"),
        ("paper_rulesets", "analysis", "JSON"),
        ("paper_rulesets", "analyzed_at", "DATETIME"),
    ]
    with engine.connect() as conn:
        for table, column, col_type in migrations:
            if table in insp.get_table_names():
                existing = [c["name"] for c in insp.get_columns(table)]
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                    conn.commit()


def _migrate_t2s():
    from .services.t2s import convert as t2s

    def _t2s_json(obj):
        if isinstance(obj, str):
            return t2s(obj)
        if isinstance(obj, list):
            return [_t2s_json(v) for v in obj]
        if isinstance(obj, dict):
            return {k: _t2s_json(v) for k, v in obj.items()}
        return obj

    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, llm_reason, analysis FROM paper_rulesets WHERE llm_reason IS NOT NULL"
        )).fetchall()
        for row_id, reason, analysis in rows:
            new_reason = t2s(reason) if reason else reason
            new_analysis = None
            if analysis:
                try:
                    parsed = json.loads(analysis) if isinstance(analysis, str) else analysis
                    new_analysis = json.dumps(_t2s_json(parsed), ensure_ascii=False)
                except (json.JSONDecodeError, TypeError):
                    new_analysis = analysis
            if new_reason != reason or new_analysis != analysis:
                conn.execute(text(
                    "UPDATE paper_rulesets SET llm_reason = :reason, analysis = :analysis WHERE id = :id"
                ), {"reason": new_reason, "analysis": new_analysis, "id": row_id})
        conn.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_add_columns()
    _migrate_t2s()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
