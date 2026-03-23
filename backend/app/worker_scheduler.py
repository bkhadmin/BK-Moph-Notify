import asyncio
import json
import time
from datetime import timedelta

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.repositories.schedule_jobs import get_due_jobs, get_by_id, update_item
from app.repositories.schedule_job_logs import create_item as create_job_log
from app.repositories.message_templates import get_by_id as get_template
from app.repositories.approved_queries import get_by_id as get_query
from app.services.hosxp_query import preview_query
from app.services.flex_template_merger import build_flex_payload_from_template_rows
from app.services.dynamic_template_renderer import build_dynamic_template_payload
from app.services.scheduler_service import compute_following_next_run, scheduler_now
from app.services.template_render import build_message_payload
from app.services.send_pipeline import send_with_log

POLL_SECONDS = 30

def ensure_tables():
    Base.metadata.create_all(bind=engine)

def _job_config(job):
    try:
        return json.loads(job.payload_json or "{}")
    except Exception:
        return {}

def _build_messages(db, job):
    q = get_query(db, job.approved_query_id) if job.approved_query_id else None
    t = get_template(db, job.message_template_id) if job.message_template_id else None
    if not q or not t:
        raise ValueError("approved query หรือ message template ไม่พบ")
    data = preview_query(q.sql_text, max_rows=q.max_rows)
    rows = data.get("rows") or []
    dynamic_payload = build_dynamic_template_payload(t.template_type, t.content, t.alt_text, rows)
    if dynamic_payload is not None:
        messages = dynamic_payload
    elif t.template_type == "flex":
        messages = build_flex_payload_from_template_rows(t.content, t.alt_text, rows)
    else:
        messages = [build_message_payload(t.template_type, t.content, t.alt_text, row) for row in rows[:10]]
    return rows, messages

def _safe_create_log(db, **kwargs):
    try:
        create_job_log(db, **kwargs)
    except Exception:
        db.rollback()

def _detail(job):
    return f"schedule_job_id={job.id}, approved_query_id={job.approved_query_id}, template_id={job.message_template_id}, notify_room_id={getattr(job, 'notify_room_id', None)}"

def _finalize_success(db, job, now, rows, messages, result):
    _safe_create_log(
        db,
        schedule_job_id=job.id,
        run_at=now,
        status="success",
        rows_returned=len(rows),
        sent_count=len(messages),
        detail_json=json.dumps(result, ensure_ascii=False),
    )
    cfg = _job_config(job)
    cfg["retry_count"] = 0
    next_run = compute_following_next_run(job, base=now)
    update_item(
        db,
        job,
        last_run_at=now,
        next_run_at=next_run,
        is_active="N" if job.schedule_type == "once" else job.is_active,
        payload_json=json.dumps(cfg, ensure_ascii=False),
    )
    print(f"[scheduler] success job_id={job.id} rows={len(rows)} sent={len(messages)} next_run_at={next_run} room_id={getattr(job, 'notify_room_id', None)}")

def _finalize_failure(db, job, now, rows, messages, exc):
    db.rollback()
    cfg = _job_config(job)
    retry_limit = int(cfg.get("retry_limit", 3))
    retry_count = int(cfg.get("retry_count", 0)) + 1
    cfg["retry_count"] = retry_count
    _safe_create_log(
        db,
        schedule_job_id=job.id,
        run_at=now,
        status="failed",
        rows_returned=len(rows) if rows else 0,
        sent_count=len(messages) if messages else 0,
        error_message=str(exc),
        detail_json=json.dumps(cfg, ensure_ascii=False),
    )
    if retry_count < retry_limit:
        next_run = now + timedelta(minutes=5)
        update_item(db, job, last_run_at=now, next_run_at=next_run, payload_json=json.dumps(cfg, ensure_ascii=False))
    else:
        cfg["retry_count"] = 0
        next_run = compute_following_next_run(job, base=now) if job.schedule_type != "once" else None
        update_item(
            db,
            job,
            last_run_at=now,
            next_run_at=next_run,
            is_active="N" if job.schedule_type == "once" else job.is_active,
            payload_json=json.dumps(cfg, ensure_ascii=False),
        )
    print(f"[scheduler] failed job_id={job.id} error={exc} next_run_at={next_run} retry_count={cfg.get('retry_count')} room_id={getattr(job, 'notify_room_id', None)}")

def execute_job(db, job):
    now = scheduler_now()
    rows = []
    messages = []
    try:
        rows, messages = _build_messages(db, job)
        result, send_log_id = asyncio.run(
            send_with_log(
                db,
                "scheduler",
                messages,
                _detail(job),
                notify_room_id=getattr(job, "notify_room_id", None),
            )
        )
        result = dict(result or {})
        result["send_log_id"] = send_log_id
        _finalize_success(db, job, now, rows, messages, result)
        return {"status": "success", "rows": len(rows), "sent": len(messages), "send_log_id": send_log_id}
    except Exception as exc:
        _finalize_failure(db, job, now, rows, messages, exc)
        return {"status": "failed", "error": str(exc), "rows": len(rows), "sent": len(messages)}

def run_job_now(job_id: int):
    ensure_tables()
    db = SessionLocal()
    try:
        job = get_by_id(db, job_id)
        if not job:
            return {"status": "not_found"}
        return execute_job(db, job)
    finally:
        db.close()

def run_once():
    ensure_tables()
    db = SessionLocal()
    try:
        now = scheduler_now()
        jobs = get_due_jobs(db, now)
        print(f"[scheduler] now={now} due_jobs={[j.id for j in jobs]}")
        for job in jobs:
            execute_job(db, job)
    finally:
        db.close()

def main():
    ensure_tables()
    print("[scheduler] worker started")
    while True:
        run_once()
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
