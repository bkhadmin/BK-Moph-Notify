from sqlalchemy.orm import Session
from app.models.message_template import MessageTemplate


def list_templates(db: Session):
    return db.query(MessageTemplate).order_by(MessageTemplate.id.desc()).all()


def create_template(db: Session, name: str, content: str):
    item = MessageTemplate(name=name, content=content, template_type="text")
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_template(db: Session, item_id: int):
    item = db.query(MessageTemplate).filter(MessageTemplate.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return item
