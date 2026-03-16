import json
import time
from datetime import datetime
from app.db.session import SessionLocal
from app.repositories.schedule_jobs import get_due_jobs, update_item
from app.repositories.schedule_job_logs import create_item as create_job_log
from app.repositories.message_templates import get_by_id as get_template
from app.repositories.approved_queries import get_by_id as get_query
from app.services.query_runner import preview_query
from app.services.flex_template_merger import build_flex_payload_from_template_rows
from app.services.moph_notify import send_messages
from app.services.scheduler_service import compute_following_next_run
from app.services.message_renderer import build_message_payload

POLL_SECONDS = 30

def run_once():
    db = SessionLocal()
    try:
        now = datetime.now()
        jobs = get_due_jobs(db, now)
        for job in jobs:
            rows = []
            messages = []
            try:
                q = get_query(db, job.approved_query_id) if job.approved_query_id else None
                t = get_template(db, job.message_template_id) if job.message_template_id else None
                if not q or not t:
                    raise ValueError("approved query หรือ message template ไม่พบ")
                data = preview_query(q.sql_text, max_rows=q.max_rows)
                rows = data.get("rows") or []
                if t.template_type == "flex":
                    messages = build_flex_payload_from_template_rows(t.content, t.alt_text, rows)
                else:
                    messages = [build_message_payload(t.template_type, t.content, t.alt_text, row) for row in rows[:10]]
                result = send_messages(messages)
                create_job_log(
                    db,
                    schedule_job_id=job.id,
                    status="success",
                    rows_returned=len(rows),
                    sent_count=len(messages),
                    detail_json=json.dumps(result, ensure_ascii=False)
                )
                next_run = compute_following_next_run(job.schedule_type, job.cron_value, job.interval_minutes, last_base=now)
                update_item(db, job, last_run_at=now, next_run_at=next_run, is_active='N' if job.schedule_type == 'once' else job.is_active)
            except Exception as exc:
                create_job_log(
                    db,
                    schedule_job_id=job.id,
                    status="failed",
                    rows_returned=len(rows) if rows else 0,
                    sent_count=len(messages) if messages else 0,
                    error_message=str(exc),
                )
                next_run = compute_following_next_run(job.schedule_type, job.cron_value, job.interval_minutes, last_base=now) if job.schedule_type != 'once' else None
                update_item(db, job, last_run_at=now, next_run_at=next_run, is_active='N' if job.schedule_type == 'once' else job.is_active)
    finally:
        db.close()

def main():
    while True:
        run_once()
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
