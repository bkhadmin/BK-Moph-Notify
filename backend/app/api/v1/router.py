from fastapi import APIRouter
from app.api.v1.audit import router as audit_router
from app.api.v1.messages import router as messages_router
from app.api.v1.queries import router as queries_router
from app.api.v1.users import router as users_router
from app.api.v1.templates import router as templates_router

api_router = APIRouter()
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_router.include_router(messages_router, prefix="/messages", tags=["messages"])
api_router.include_router(queries_router, prefix="/queries", tags=["queries"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(templates_router, prefix="/templates", tags=["templates"])
