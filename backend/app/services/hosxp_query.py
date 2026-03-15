from sqlalchemy import create_engine, text
from app.core.config import settings
from app.services.sql_guard import ensure_safe_select

def preview_query(sql_text:str, max_rows:int|None=None)->dict:
    ok, reason = ensure_safe_select(sql_text)
    if not ok:
        raise ValueError(reason)
    limit = min(max_rows or settings.max_query_rows, settings.max_query_rows)
    wrapped = f"SELECT * FROM ({sql_text}) _bk_limit LIMIT {limit}"
    engine = create_engine(settings.hosxp_database_uri, pool_pre_ping=True, connect_args={'read_timeout': settings.max_query_seconds, 'write_timeout': settings.max_query_seconds})
    with engine.connect() as conn:
        result = conn.execute(text(wrapped))
        rows = [dict(r._mapping) for r in result]
    return {"columns": list(rows[0].keys()) if rows else [], "rows": rows, "row_count": len(rows)}
