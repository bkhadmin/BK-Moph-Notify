from sqlalchemy.orm import Session
from app.models.approved_query import ApprovedQuery


def list_queries(db: Session):
    return db.query(ApprovedQuery).order_by(ApprovedQuery.id.desc()).all()


def create_query(db: Session, name: str, sql_text: str):
    item = ApprovedQuery(name=name, sql_text=sql_text)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_query(db: Session, item_id: int):
    item = db.query(ApprovedQuery).filter(ApprovedQuery.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return item
