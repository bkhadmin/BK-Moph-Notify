from sqlalchemy.orm import Session
from app.models.approved_query import ApprovedQuery
def get_all(db:Session): return db.query(ApprovedQuery).order_by(ApprovedQuery.id.desc()).all()
def get_active(db:Session): return db.query(ApprovedQuery).filter(ApprovedQuery.is_active=='Y').order_by(ApprovedQuery.id.desc()).all()
def get_by_id(db:Session, item_id:int): return db.query(ApprovedQuery).filter(ApprovedQuery.id==item_id).first()
def create_item(db:Session, name:str, sql_text:str, max_rows:int):
    row=ApprovedQuery(name=name, sql_text=sql_text, max_rows=max_rows); db.add(row); db.commit(); db.refresh(row); return row
