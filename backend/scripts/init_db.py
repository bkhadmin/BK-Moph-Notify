from sqlalchemy.orm import Session
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models import Role, User
from app.core.config import settings
from app.core.security import hash_password


def main():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        role = db.query(Role).filter(Role.code == "superadmin").first()
        if not role:
            role = Role(code="superadmin", name="Super Admin", is_system=True)
            db.add(role)
            db.flush()

        user = db.query(User).filter(User.username == settings.internal_superadmin_username).first()
        if not user:
            db.add(
                User(
                    username=settings.internal_superadmin_username,
                    password_hash=hash_password(settings.internal_superadmin_password),
                    display_name="Super Admin",
                    auth_type="local",
                    role_id=role.id,
                )
            )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
