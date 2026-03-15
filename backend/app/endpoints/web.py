import json
from datetime import datetime
from fastapi import APIRouter,Request,Form,Depends,status,HTTPException,UploadFile,File
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.csrf import new_token,valid
from app.core.session import create_session,get_session,destroy_session
from app.core.security import verify_password
from app.db.session import get_db
from app.repositories.users import get_by_username,get_all as get_users,upsert_provider_user
from app.repositories.roles import get_by_code,get_all as get_roles
from app.repositories.permissions import get_all as get_permissions
from app.repositories.access_logs import write_log,get_all as get_access_logs
from app.repositories.ip_bans import get_by_ip,touch_fail,clear_fail
from app.repositories.role_permissions import set_role_permissions,get_permission_codes_for_role
from app.repositories.approved_queries import get_all as get_queries, create_item as create_query, get_by_id as get_query_by_id
from app.repositories.message_templates import get_all as get_templates, create_item as create_template, get_by_id as get_template_by_id
from app.repositories.schedule_jobs import get_all as get_jobs, create_item as create_job
from app.repositories.send_logs import get_all as get_send_logs
from app.repositories.media_files import create_item as create_media, get_all as get_media
from app.repositories.delivery_statuses import get_all as get_delivery_statuses
from app.repositories.provider_profiles import get_all as get_provider_profiles, get_by_id as get_provider_profile_by_id, update_profile_manual
from app.repositories.provider_profile_histories import get_all_for_profile
from app.services.rbac import allowed_menu
from app.services.provider_auth import provider_login_url,exchange_profile,test_provider_config
from app.services.hosxp_query import preview_query, test_connection
from app.services.sql_guard import ensure_safe_select
from app.services.template_render import render_text_template, build_message_payload
from app.services.scheduler_service import parse_next_run
from app.services.media_service import save_resized_image
from app.services.send_pipeline import send_with_log
from app.services.csv_export import to_csv_bytes
from app.services.xlsx_export import to_xlsx_bytes
from app.services.delivery_reconcile import ingest_status_callback
from app.services.pagination import paginate
from app.services.chart_data import counter_from_rows
from app.services.moph_notify import health_check as moph_notify_health_check

router=APIRouter()
templates=Jinja2Templates(directory='app/templates')

def client_ip(request:Request)->str:
    return request.headers.get('x-forwarded-for', request.client.host if request.client else 'unknown').split(',')[0].strip()

def get_current_session(request:Request):
    return get_session(request.cookies.get(settings.session_cookie_name))

def _filter_rows(rows, keyword:str):
    if not keyword:
        return rows
    k = keyword.lower()
    out = []
    for row in rows:
        text = ' '.join('' if v is None else str(v) for v in row.values()).lower()
        if k in text:
            out.append(row)
    return out

def require_session(request:Request):
    session = get_current_session(request)
    if not session:
        raise HTTPException(status_code=401, detail='not authenticated')
    return session

def require_menu(db:Session, session:dict, menu_code:str):
    if not allowed_menu(db, session.get('role_id'), menu_code):
        raise HTTPException(status_code=403, detail='forbidden')

def ctx(request:Request, db:Session, session:dict|None, **extra):
    role_id=session.get('role_id') if session else None
    menus={
        'dashboard':allowed_menu(db,role_id,'dashboard'),
        'users':allowed_menu(db,role_id,'users'),
        'logs':allowed_menu(db,role_id,'logs'),
        'rbac':allowed_menu(db,role_id,'rbac'),
        'notify':allowed_menu(db,role_id,'notify'),
        'queries':allowed_menu(db,role_id,'queries'),
        'templates':allowed_menu(db,role_id,'templates'),
        'schedules':allowed_menu(db,role_id,'schedules'),
        'media':allowed_menu(db,role_id,'media'),
    }
    data={'request':request,'session':session,'menus':menus}
    data.update(extra)
    return data

def render_login(request:Request, error:str|None=None):
    token=new_token()
    response=templates.TemplateResponse('auth/login.html', {'request':request,'csrf_token':token,'error':error,'provider_login_enabled':settings.provider_login_enabled})
    response.set_cookie(settings.csrf_cookie_name, token, httponly=False, samesite=settings.session_cookie_samesite, path='/')
    return response

@router.get('/health')
def health(): return {'status':'ok','app':settings.app_name}

@router.get('/login')
def login_page(request:Request, error:str|None=None):
    return render_login(request, error)

@router.post('/login')
def login(request:Request, username:str=Form(...), password:str=Form(...), csrf_token:str=Form(...), db:Session=Depends(get_db)):
    ip=client_ip(request)
    ban=get_by_ip(db, ip)
    if ban and ban.is_banned=='Y':
        write_log(db, username, ip, 'login.local', 'blocked', 'IP banned')
        raise HTTPException(status_code=403, detail='IP banned')
    cookie_token=request.cookies.get(settings.csrf_cookie_name)
    if settings.csrf_enabled and not valid(cookie_token, csrf_token):
        write_log(db, username, ip, 'login.local', 'failed', 'csrf validation failed')
        return render_login(request, 'CSRF validation failed')
    user=get_by_username(db, username)
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        row=touch_fail(db, ip, settings.ip_ban_threshold)
        write_log(db, username, ip, 'login.local', 'failed', f'invalid credential fail_count={row.fail_count}')
        return render_login(request, 'Username หรือ Password ไม่ถูกต้อง')
    clear_fail(db, ip)
    sid=create_session({'user_id':user.id,'username':user.username,'display_name':user.display_name,'role_id':user.role_id})
    write_log(db, user.username, ip, 'login.local', 'success', None)
    response=RedirectResponse('/dashboard', status_code=302)
    response.set_cookie(settings.session_cookie_name, sid, httponly=True, samesite=settings.session_cookie_samesite, path='/')
    return response

@router.get('/auth/provider/login')
def provider_login():
    return RedirectResponse(provider_login_url(), status_code=302)

@router.get('/api/v1/auth/provider/callback')
async def provider_callback(request:Request, code:str|None=None, error:str|None=None, db:Session=Depends(get_db)):
    ip=client_ip(request)
    if error:
        write_log(db, None, ip, 'login.provider', 'failed', f'provider_error={error}')
        return render_login(request, f'Provider login failed: {error}')
    if not code:
        write_log(db, None, ip, 'login.provider', 'failed', 'missing authorization code')
        return render_login(request, 'Provider login failed: missing authorization code')
    try:
        profile=await exchange_profile(code)
        default_role=get_by_code(db, 'user')
        user=upsert_provider_user(db, profile, default_role.id if default_role else None)
        sid=create_session({'user_id':user.id,'username':user.username,'display_name':user.display_name,'role_id':user.role_id})
        write_log(db, user.username, ip, 'login.provider', 'success', f"provider_id={profile.get('provider_id')}")
        response=RedirectResponse('/dashboard', status_code=302)
        response.set_cookie(settings.session_cookie_name, sid, httponly=True, samesite=settings.session_cookie_samesite, path='/')
        return response
    except Exception as exc:
        write_log(db, None, ip, 'login.provider', 'failed', str(exc))
        return render_login(request, f'Provider callback error: {exc}')

@router.post('/api/v1/notify/status/callback')
async def notify_status_callback(request:Request, db:Session=Depends(get_db)):
    payload = await request.json()
    result = ingest_status_callback(db, payload)
    return result

@router.get('/dashboard')
def dashboard(request:Request, db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'dashboard')
    return templates.TemplateResponse('admin/dashboard.html', ctx(request, db, session, users=get_users(db), logs=get_access_logs(db), send_logs=get_send_logs(db), jobs=get_jobs(db), media_files=get_media(db), delivery_statuses=get_delivery_statuses(db), provider_profiles=get_provider_profiles(db)))

@router.get('/system/connections')
async def system_connections(request:Request, db:Session=Depends(get_db)):
    session=require_session(request)
    logs_menu = allowed_menu(db, session.get('role_id'), 'logs')
    if not logs_menu:
        raise HTTPException(status_code=403, detail='forbidden')
    try:
        hosxp_result = test_connection()
    except Exception as exc:
        hosxp_result = {"status": "failed", "detail": str(exc)}
    try:
        provider_result = await test_provider_config()
    except Exception as exc:
        provider_result = {"status": "failed", "detail": str(exc)}
    try:
        notify_result = await moph_notify_health_check()
    except Exception as exc:
        notify_result = {"status": "failed", "detail": str(exc)}
    return templates.TemplateResponse('admin/system_connections.html', ctx(request, db, session, hosxp_result=hosxp_result, provider_result=provider_result, notify_result=notify_result))

@router.get('/reports')
def reports_page(request:Request, db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'logs')
    access_rows = [{"status": x.status} for x in get_access_logs(db)]
    send_rows = [{"status": x.status} for x in get_send_logs(db)]
    delivery_rows = [{"status": x.status} for x in get_delivery_statuses(db)]
    summary = {
        "users": len(get_users(db)),
        "access_logs": len(access_rows),
        "send_logs": len(send_rows),
        "delivery_statuses": len(delivery_rows),
        "provider_profiles": len(get_provider_profiles(db)),
        "media_files": len(get_media(db)),
        "schedules": len(get_jobs(db)),
        "approved_queries": len(get_queries(db)),
        "templates": len(get_templates(db)),
    }
    charts = {
        "access_status": counter_from_rows(access_rows, "status"),
        "send_status": counter_from_rows(send_rows, "status"),
        "delivery_status": counter_from_rows(delivery_rows, "status"),
    }
    return templates.TemplateResponse('admin/reports.html', ctx(request, db, session, summary=summary, charts=charts))

@router.get('/users')
def users_page(request:Request, db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'users')
    return templates.TemplateResponse('admin/users.html', ctx(request, db, session, users=get_users(db)))

@router.get('/profiles')
def profiles_page(request:Request, q:str='', page:int=1, per_page:int=20, db:Session=Depends(get_db)):
    session=require_session(request)
    rows = [{
        "id": x.id, "user_id": x.user_id, "account_id": x.account_id, "provider_id": x.provider_id,
        "name_th": x.name_th, "organization_name": x.organization_name, "organization_code": x.organization_code,
        "position_name": x.position_name, "license_no": x.license_no, "phone": x.phone, "email": x.email
    } for x in get_provider_profiles(db)]
    rows = _filter_rows(rows, q)
    pager = paginate(rows, page=page, per_page=per_page)
    return templates.TemplateResponse('admin/profiles.html', ctx(request, db, session, profile_rows=pager["items"], keyword=q, pager=pager))

@router.get('/profiles/{profile_id}')
def profile_detail_page(profile_id:int, request:Request, db:Session=Depends(get_db)):
    session=require_session(request)
    row = get_provider_profile_by_id(db, profile_id)
    if not row:
        raise HTTPException(status_code=404, detail='profile not found')
    history = get_all_for_profile(db, profile_id)
    return templates.TemplateResponse('admin/profile_detail.html', ctx(request, db, session, profile=row, history_rows=history))

@router.post('/profiles/{profile_id}')
def profile_update_page(profile_id:int, request:Request, name_th:str=Form(''), position_name:str=Form(''), organization_name:str=Form(''), organization_code:str=Form(''), license_no:str=Form(''), phone:str=Form(''), email:str=Form(''), db:Session=Depends(get_db)):
    session=require_session(request)
    row = get_provider_profile_by_id(db, profile_id)
    if not row:
        raise HTTPException(status_code=404, detail='profile not found')
    payload = {
        "name_th": name_th,
        "position_name": position_name,
        "organization_name": organization_name,
        "organization_code": organization_code,
        "license_no": license_no,
        "phone": phone,
        "email": email,
    }
    update_profile_manual(db, row, payload, changed_by=session.get('username'))
    write_log(db, session.get('username'), client_ip(request), 'profile.update', 'success', f'profile_id={profile_id}')
    return RedirectResponse(f'/profiles/{profile_id}', status_code=302)

@router.get('/profiles/export')
def profiles_export(request:Request, q:str='', format:str='csv', db:Session=Depends(get_db)):
    session=require_session(request)
    rows = [{
        "id": x.id, "user_id": x.user_id, "account_id": x.account_id, "provider_id": x.provider_id,
        "name_th": x.name_th, "organization_name": x.organization_name, "organization_code": x.organization_code,
        "position_name": x.position_name, "license_no": x.license_no, "phone": x.phone, "email": x.email
    } for x in get_provider_profiles(db)]
    rows = _filter_rows(rows, q)
    if format == 'xlsx':
        data = to_xlsx_bytes(rows, sheet_name='provider_profiles')
        return Response(content=data, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': 'attachment; filename=provider_profiles.xlsx'})
    data = to_csv_bytes(rows)
    return Response(content=data, media_type='text/csv; charset=utf-8', headers={'Content-Disposition': 'attachment; filename=provider_profiles.csv'})

@router.get('/logs/access')
def access_logs_page(request:Request, q:str='', page:int=1, per_page:int=20, db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'logs')
    access_rows = [{"actor": x.actor, "ip_address": x.ip_address, "action": x.action, "status": x.status, "detail": x.detail} for x in get_access_logs(db)]
    send_rows = [{"id": x.id, "actor": x.actor, "channel": x.channel, "status": x.status, "retry_count": x.retry_count, "detail": x.detail} for x in get_send_logs(db)]
    delivery_rows = [{"send_log_id": x.send_log_id, "external_message_id": x.external_message_id, "status": x.status, "provider_status": x.provider_status, "detail": x.detail} for x in get_delivery_statuses(db)]
    access_rows = _filter_rows(access_rows, q)
    send_rows = _filter_rows(send_rows, q)
    delivery_rows = _filter_rows(delivery_rows, q)
    access_pager = paginate(access_rows, page=page, per_page=per_page)
    send_pager = paginate(send_rows, page=page, per_page=per_page)
    delivery_pager = paginate(delivery_rows, page=page, per_page=per_page)
    return templates.TemplateResponse('admin/access_logs.html', ctx(request, db, session, logs=access_pager["items"], send_logs=send_pager["items"], delivery_statuses=delivery_pager["items"], keyword=q, pager=access_pager))

@router.get('/logs/export/{kind}')
def logs_export(kind:str, request:Request, q:str='', format:str='csv', db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'logs')
    if kind == 'access':
        rows = [{"actor": x.actor, "ip_address": x.ip_address, "action": x.action, "status": x.status, "detail": x.detail} for x in get_access_logs(db)]
    elif kind == 'send':
        rows = [{"id": x.id, "actor": x.actor, "channel": x.channel, "status": x.status, "retry_count": x.retry_count, "detail": x.detail} for x in get_send_logs(db)]
    else:
        rows = [{"send_log_id": x.send_log_id, "external_message_id": x.external_message_id, "status": x.status, "provider_status": x.provider_status, "detail": x.detail} for x in get_delivery_statuses(db)]
    rows = _filter_rows(rows, q)
    if format == 'xlsx':
        data = to_xlsx_bytes(rows, sheet_name=f'{kind}_logs')
        return Response(content=data, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename={kind}_logs.xlsx'})
    data = to_csv_bytes(rows)
    return Response(content=data, media_type='text/csv; charset=utf-8', headers={'Content-Disposition': f'attachment; filename={kind}_logs.csv'})

@router.get('/queries')
def queries_page(request:Request, db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'queries')
    return templates.TemplateResponse('admin/queries.html', ctx(request, db, session, queries=get_queries(db), preview=None, error=None, hosxp_test=None))

@router.post('/queries')
def create_query_page(request:Request, name:str=Form(...), sql_text:str=Form(...), max_rows:int=Form(100), db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'queries')
    ok, reason = ensure_safe_select(sql_text)
    if ok:
        create_query(db, name, sql_text, max_rows)
        write_log(db, session.get('username'), client_ip(request), 'query.create', 'success', name)
        return RedirectResponse('/queries', status_code=302)
    return templates.TemplateResponse('admin/queries.html', ctx(request, db, session, queries=get_queries(db), preview=None, error=reason, hosxp_test=None))

@router.post('/queries/preview')
def preview_query_page(request:Request, sql_text:str=Form(...), max_rows:int=Form(20), db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'queries')
    try:
        preview = preview_query(sql_text, max_rows=max_rows)
        write_log(db, session.get('username'), client_ip(request), 'query.preview', 'success', f"rows={preview['row_count']}")
        return templates.TemplateResponse('admin/queries.html', ctx(request, db, session, queries=get_queries(db), preview=preview, error=None, hosxp_test=None))
    except Exception as exc:
        write_log(db, session.get('username'), client_ip(request), 'query.preview', 'failed', str(exc))
        return templates.TemplateResponse('admin/queries.html', ctx(request, db, session, queries=get_queries(db), preview=None, error=str(exc), hosxp_test=None))

@router.post('/queries/test-connection')
def query_test_connection(request:Request, db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'queries')
    try:
        result = test_connection()
        write_log(db, session.get('username'), client_ip(request), 'query.test_connection', 'success', json.dumps(result, ensure_ascii=False))
        return templates.TemplateResponse('admin/queries.html', ctx(request, db, session, queries=get_queries(db), preview=None, error=None, hosxp_test=result))
    except Exception as exc:
        write_log(db, session.get('username'), client_ip(request), 'query.test_connection', 'failed', str(exc))
        return templates.TemplateResponse('admin/queries.html', ctx(request, db, session, queries=get_queries(db), preview=None, error=None, hosxp_test={"status":"failed","detail":str(exc)}))

@router.get('/templates')
def templates_page(request:Request, db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'templates')
    flex_sample = '{"type":"bubble","body":{"type":"box","layout":"vertical","contents":[{"type":"text","text":"สวัสดี {name}"},{"type":"text","text":"หน่วยงาน {organization_name}","size":"sm"}]}}'
    return templates.TemplateResponse('admin/templates.html', ctx(request, db, session, message_templates=get_templates(db), render_result=None, media_files=get_media(db), flex_sample=flex_sample))

@router.post('/templates')
def create_template_page(request:Request, name:str=Form(...), template_type:str=Form(...), content:str=Form(...), alt_text:str=Form(''), db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'templates')
    create_template(db, name, template_type, content, alt_text or None)
    write_log(db, session.get('username'), client_ip(request), 'template.create', 'success', name)
    return RedirectResponse('/templates', status_code=302)

@router.post('/templates/render')
def render_template_page(request:Request, content:str=Form(...), variables_json:str=Form('{}'), db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'templates')
    variables = json.loads(variables_json or '{}')
    render_result = render_text_template(content, variables)
    write_log(db, session.get('username'), client_ip(request), 'template.render', 'success', None)
    flex_sample = '{"type":"bubble","body":{"type":"box","layout":"vertical","contents":[{"type":"text","text":"สวัสดี {name}"},{"type":"text","text":"หน่วยงาน {organization_name}","size":"sm"}]}}'
    return templates.TemplateResponse('admin/templates.html', ctx(request, db, session, message_templates=get_templates(db), render_result=render_result, media_files=get_media(db), flex_sample=flex_sample))

@router.get('/media')
def media_page(request:Request, db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'media')
    return templates.TemplateResponse('admin/media.html', ctx(request, db, session, media_files=get_media(db)))

@router.post('/media')
async def media_upload(request:Request, image:UploadFile=File(...), db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'media')
    content = await image.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail='File too large')
    saved = save_resized_image(content, image.filename or 'upload.jpg', image.content_type)
    create_media(db, image.filename or saved['stored_name'], saved['stored_name'], saved['mime_type'], saved['width'], saved['height'], saved['public_url'])
    write_log(db, session.get('username'), client_ip(request), 'media.upload', 'success', saved['public_url'])
    return RedirectResponse('/media', status_code=302)

@router.get('/notify/test')
def notify_page(request:Request, db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'notify')
    return templates.TemplateResponse('admin/notify_test.html', ctx(request, db, session, result=None, send_error=None, template_payload=None, data_rows=None, approved_queries=get_queries(db), message_templates=get_templates(db), media_files=get_media(db)))

@router.post('/notify/test')
async def notify_send(request:Request, message_text:str=Form(...), db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'notify')
    payload=[{"type":"text","text":message_text}]
    try:
        result, _ = await send_with_log(db, session.get('username'), payload, 'manual text send')
        write_log(db, session.get('username'), client_ip(request), 'notify.send', 'success', 'manual text send')
        return templates.TemplateResponse('admin/notify_test.html', ctx(request, db, session, result=result, send_error=None, template_payload=payload, data_rows=None, approved_queries=get_queries(db), message_templates=get_templates(db), media_files=get_media(db)))
    except Exception as exc:
        write_log(db, session.get('username'), client_ip(request), 'notify.send', 'failed', str(exc))
        return templates.TemplateResponse('admin/notify_test.html', ctx(request, db, session, result=None, send_error=str(exc), template_payload=payload, data_rows=None, approved_queries=get_queries(db), message_templates=get_templates(db), media_files=get_media(db)))

@router.post('/notify/preview')
def notify_preview(request:Request, approved_query_id:int=Form(...), message_template_id:int=Form(...), db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'notify')
    q = get_query_by_id(db, approved_query_id)
    t = get_template_by_id(db, message_template_id)
    data = preview_query(q.sql_text, max_rows=q.max_rows)
    first_row = data['rows'][0] if data['rows'] else {}
    payload = build_message_payload(t.template_type, t.content, t.alt_text, first_row)
    return templates.TemplateResponse('admin/notify_test.html', ctx(request, db, session, result=None, send_error=None, template_payload=payload, data_rows=data['rows'][:10], approved_queries=get_queries(db), message_templates=get_templates(db), media_files=get_media(db)))

@router.post('/notify/send-from-template')
async def notify_send_from_template(request:Request, approved_query_id:int=Form(...), message_template_id:int=Form(...), db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'notify')
    q = get_query_by_id(db, approved_query_id)
    t = get_template_by_id(db, message_template_id)
    data = preview_query(q.sql_text, max_rows=q.max_rows)
    messages = [build_message_payload(t.template_type, t.content, t.alt_text, row) for row in data['rows']]
    try:
        result, _ = await send_with_log(db, session.get('username'), messages, f'approved_query_id={q.id}, template_id={t.id}')
        write_log(db, session.get('username'), client_ip(request), 'notify.send.template', 'success', f'rows={len(messages)}')
        return templates.TemplateResponse('admin/notify_test.html', ctx(request, db, session, result=result, send_error=None, template_payload=messages[:3], data_rows=data['rows'][:10], approved_queries=get_queries(db), message_templates=get_templates(db), media_files=get_media(db)))
    except Exception as exc:
        write_log(db, session.get('username'), client_ip(request), 'notify.send.template', 'failed', str(exc))
        return templates.TemplateResponse('admin/notify_test.html', ctx(request, db, session, result=None, send_error=str(exc), template_payload=messages[:3], data_rows=data['rows'][:10], approved_queries=get_queries(db), message_templates=get_templates(db), media_files=get_media(db)))

@router.get('/schedules')
def schedules_page(request:Request, db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'schedules')
    return templates.TemplateResponse('admin/schedules.html', ctx(request, db, session, jobs=get_jobs(db), approved_queries=get_queries(db), message_templates=get_templates(db)))

@router.post('/schedules')
def schedules_create(request:Request, name:str=Form(...), schedule_type:str=Form(...), cron_value:str=Form(''), interval_minutes:int=Form(0), approved_query_id:int=Form(None), message_template_id:int=Form(None), db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'schedules')
    next_run_at = parse_next_run(schedule_type, cron_value or None, interval_minutes or None, base=datetime.now())
    create_job(db, name, schedule_type, cron_value or None, interval_minutes or None, approved_query_id, message_template_id, {}, next_run_at)
    write_log(db, session.get('username'), client_ip(request), 'schedule.create', 'success', name)
    return RedirectResponse('/schedules', status_code=302)

@router.get('/rbac')
def rbac_page(request:Request, db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'rbac')
    roles=get_roles(db); permissions=get_permissions(db); role_map={r.id:get_permission_codes_for_role(db,r.id) for r in roles}
    return templates.TemplateResponse('admin/rbac.html', ctx(request, db, session, roles=roles, permissions=permissions, role_map=role_map))

@router.post('/rbac/role/{role_id}')
def rbac_update(role_id:int, request:Request, permission_ids:list[int]=Form(default=[]), db:Session=Depends(get_db)):
    session=require_session(request)
    require_menu(db, session, 'rbac')
    set_role_permissions(db, role_id, permission_ids)
    write_log(db, session.get('username'), client_ip(request), 'rbac.update', 'success', f'role_id={role_id}')
    return RedirectResponse('/rbac', status_code=302)

@router.get('/logout')
def logout(request:Request, db:Session=Depends(get_db)):
    session=get_current_session(request)
    if session: write_log(db, session.get('username'), client_ip(request), 'logout', 'success', None)
    destroy_session(request.cookies.get(settings.session_cookie_name))
    response=RedirectResponse('/login', status_code=302)
    response.delete_cookie(settings.session_cookie_name, path='/')
    response.delete_cookie(settings.csrf_cookie_name, path='/')
    return response
