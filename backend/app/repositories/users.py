from sqlalchemy.orm import Session
from app.models.user import User


def get_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_all(db: Session):
    return db.query(User).order_by(User.id.desc()).all()


def create_local_user(db: Session, username: str, password_hash: str, display_name: str | None = None, role_id: int | None = None):
    item = User(username=username, password_hash=password_hash, display_name=display_name, auth_type="local", role_id=role_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
