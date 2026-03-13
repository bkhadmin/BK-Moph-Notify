from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import api_router
from app.endpoints import web
from app.core.config import settings
from app.core.middleware import AccessLogMiddleware, CSRFMiddleware, SecurityHeadersMiddleware

app = FastAPI(title=settings.app_name)

app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

trusted_hosts = [x.strip() for x in settings.trusted_hosts.split(",") if x.strip()]
for h in ["app", "app:8000", "nginx", "bk_app", "127.0.0.1", "127.0.0.1:8000"]:
    if h not in trusted_hosts:
        trusted_hosts.append(h)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts or ["*"])
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(AccessLogMiddleware)

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


app.include_router(api_router, prefix="/api/v1")
app.include_router(web.router)
