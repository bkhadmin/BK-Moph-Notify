from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


def write_log(db: Session, actor: str | None, action: str, target_type: str | None = None, target_id: str | None = None, detail: str | None = None):
    item = AuditLog(actor=actor, action=action, target_type=target_type, target_id=target_id, detail=detail)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_logs(db: Session):
    return db.query(AuditLog).order_by(AuditLog.id.desc()).all()
