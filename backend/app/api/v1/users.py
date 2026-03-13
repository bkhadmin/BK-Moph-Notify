from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories.users import get_all

router = APIRouter()


@router.get("")
def list_users(db: Session = Depends(get_db)):
    return [{"id": x.id, "username": x.username, "display_name": x.display_name, "auth_type": x.auth_type} for x in get_all(db)]
