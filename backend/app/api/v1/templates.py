from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories.templates import list_templates, create_template, delete_template
from app.repositories.audit_logs import write_log

router = APIRouter()


@router.get("")
def get_templates(db: Session = Depends(get_db)):
    return [{"id": x.id, "name": x.name, "content": x.content} for x in list_templates(db)]


@router.post("")
def add_template(payload: dict, db: Session = Depends(get_db)):
    item = create_template(db, payload.get("name", "Sample Template"), payload.get("content", "Hello {name}"))
    write_log(db, "api", "template.create", "message_template", str(item.id), item.name)
    return {"id": item.id}


@router.delete("/{item_id}")
def remove_template(item_id: int, db: Session = Depends(get_db)):
    item = delete_template(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    write_log(db, "api", "template.delete", "message_template", str(item_id), None)
    return {"status": "deleted"}
