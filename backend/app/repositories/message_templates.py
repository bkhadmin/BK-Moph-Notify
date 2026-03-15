from sqlalchemy.orm import Session
from app.models.message_template import MessageTemplate
def get_all(db:Session): return db.query(MessageTemplate).order_by(MessageTemplate.id.desc()).all()
def get_active(db:Session): return db.query(MessageTemplate).filter(MessageTemplate.is_active=='Y').order_by(MessageTemplate.id.desc()).all()
def get_by_id(db:Session, item_id:int): return db.query(MessageTemplate).filter(MessageTemplate.id==item_id).first()
def create_item(db:Session, name:str, template_type:str, content:str, alt_text:str|None):
    row=MessageTemplate(name=name, template_type=template_type, content=content, alt_text=alt_text); db.add(row); db.commit(); db.refresh(row); return row
