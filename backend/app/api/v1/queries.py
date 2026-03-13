from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories.queries import list_queries, create_query, delete_query
from app.repositories.audit_logs import write_log
from app.services.sql_guard import ensure_safe_select

router = APIRouter()


@router.get("")
def get_queries(db: Session = Depends(get_db)):
    return [{"id": x.id, "name": x.name, "sql_text": x.sql_text} for x in list_queries(db)]


@router.post("")
def add_query(payload: dict, db: Session = Depends(get_db)):
    sql = payload.get("sql", "")
    name = payload.get("name", "Approved Query")
    ok, reason = ensure_safe_select(sql)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    item = create_query(db, name, sql)
    write_log(db, "api", "query.create", "approved_query", str(item.id), name)
    return {"id": item.id}


@router.delete("/{item_id}")
def remove_query(item_id: int, db: Session = Depends(get_db)):
    item = delete_query(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    write_log(db, "api", "query.delete", "approved_query", str(item_id), None)
    return {"status": "deleted"}
