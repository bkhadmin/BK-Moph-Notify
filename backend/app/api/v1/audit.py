from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories.audit_logs import list_logs

router = APIRouter()


@router.get("")
def get_logs(db: Session = Depends(get_db)):
    return [
        {
            "id": x.id,
            "actor": x.actor,
            "action": x.action,
            "target_type": x.target_type,
            "target_id": x.target_id,
            "detail": x.detail,
        }
        for x in list_logs(db)
    ]
