from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.csrf import new_token, valid
from app.core.session import create_session, get_session, destroy_session
from app.core.rbac import allowed_menu
from app.core.security import verify_password
from app.db.session import get_db
from app.repositories.users import get_by_username, get_all
from app.repositories.queries import list_queries, create_query, delete_query
from app.repositories.templates import list_templates, create_template, delete_template
from app.repositories.audit_logs import list_logs, write_log
from app.services.sql_guard import ensure_safe_select

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _session(request: Request):
    return get_session(request.cookies.get(settings.session_cookie_name))


def _ctx(request: Request, session: dict, **extra):
    menus = {m: allowed_menu(session.get("role"), m) for m in ["dashboard", "users", "queries", "templates", "send", "audit"]}
    data = {"request": request, "session": session, "menus": menus}
    data.update(extra)
    return data


@router.get("/login")
def login_page(request: Request):
    token = new_token()
    response = templates.TemplateResponse("login.html", {"request": request, "csrf_token": token, "error": None})
    response.set_cookie(settings.csrf_cookie_name, token, httponly=False, samesite=settings.session_cookie_samesite, path="/")
    return response


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), csrf_token: str = Form(...), db: Session = Depends(get_db)):
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    if settings.csrf_enabled and not valid(cookie_token, csrf_token):
        token = new_token()
        return templates.TemplateResponse("login.html", {"request": request, "csrf_token": token, "error": "CSRF validation failed"}, status_code=status.HTTP_403_FORBIDDEN)

    user = get_by_username(db, username)
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        token = new_token()
        return templates.TemplateResponse("login.html", {"request": request, "csrf_token": token, "error": "Username หรือ Password ไม่ถูกต้อง"}, status_code=status.HTTP_401_UNAUTHORIZED)

    role = "superadmin" if username == settings.internal_superadmin_username else "user"
    sid = create_session({"username": user.username, "role": role, "auth_type": "local", "user_id": user.id})
    write_log(db, username, "login.success", "user", str(user.id), None)
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie(settings.session_cookie_name, sid, httponly=True, samesite=settings.session_cookie_samesite, path="/")
    return response


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    session = _session(request)
    if not session:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("dashboard.html", _ctx(request, session, users=get_all(db), queries=list_queries(db), templates_list=list_templates(db)))


@router.get("/users")
def users_page(request: Request, db: Session = Depends(get_db)):
    session = _session(request)
    if not session:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("users.html", _ctx(request, session, users=get_all(db)))


@router.get("/queries")
def queries_page(request: Request, db: Session = Depends(get_db)):
    session = _session(request)
    if not session:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("queries.html", _ctx(request, session, queries=list_queries(db)))


@router.post("/queries")
def queries_create(request: Request, name: str = Form(...), sql_text: str = Form(...), db: Session = Depends(get_db)):
    session = _session(request)
    if not session:
        return RedirectResponse("/login", status_code=302)
    ok, _ = ensure_safe_select(sql_text)
    if ok:
        item = create_query(db, name, sql_text)
        write_log(db, session.get("username"), "query.create", "approved_query", str(item.id), name)
    return RedirectResponse("/queries", status_code=302)


@router.get("/queries/delete/{item_id}")
def queries_delete(item_id: int, request: Request, db: Session = Depends(get_db)):
    session = _session(request)
    if not session:
        return RedirectResponse("/login", status_code=302)
    delete_query(db, item_id)
    write_log(db, session.get("username"), "query.delete", "approved_query", str(item_id), None)
    return RedirectResponse("/queries", status_code=302)


@router.get("/templates")
def templates_page(request: Request, db: Session = Depends(get_db)):
    session = _session(request)
    if not session:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("templates.html", _ctx(request, session, templates_list=list_templates(db)))


@router.post("/templates")
def templates_create(request: Request, name: str = Form(...), content: str = Form(...), db: Session = Depends(get_db)):
    session = _session(request)
    if not session:
        return RedirectResponse("/login", status_code=302)
    item = create_template(db, name, content)
    write_log(db, session.get("username"), "template.create", "message_template", str(item.id), name)
    return RedirectResponse("/templates", status_code=302)


@router.get("/templates/delete/{item_id}")
def templates_delete(item_id: int, request: Request, db: Session = Depends(get_db)):
    session = _session(request)
    if not session:
        return RedirectResponse("/login", status_code=302)
    delete_template(db, item_id)
    write_log(db, session.get("username"), "template.delete", "message_template", str(item_id), None)
    return RedirectResponse("/templates", status_code=302)


@router.get("/send")
def send_page(request: Request):
    session = _session(request)
    if not session:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("send.html", _ctx(request, session, result=None))


@router.post("/send")
def send_preview(request: Request, template: str = Form(...), name: str = Form("User"), db: Session = Depends(get_db)):
    session = _session(request)
    if not session:
        return RedirectResponse("/login", status_code=302)
    result = template.replace("{name}", name)
    write_log(db, session.get("username"), "message.preview", "message", None, result)
    return templates.TemplateResponse("send.html", _ctx(request, session, result=result))


@router.get("/audit")
def audit_page(request: Request, db: Session = Depends(get_db)):
    session = _session(request)
    if not session:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("audit.html", _ctx(request, session, logs=list_logs(db)))


@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    session = _session(request)
    if session:
        write_log(db, session.get("username"), "logout", "user", str(session.get("user_id")), None)
    destroy_session(request.cookies.get(settings.session_cookie_name))
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    return response
