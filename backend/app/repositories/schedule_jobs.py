import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.schedule_job import ScheduleJob

def get_all(db:Session): return db.query(ScheduleJob).order_by(ScheduleJob.id.desc()).all()
def get_due_jobs(db:Session, now:datetime):
    return db.query(ScheduleJob).filter(ScheduleJob.is_active=='Y').filter(ScheduleJob.next_run_at != None).filter(ScheduleJob.next_run_at <= now).all()

def create_item(db:Session, name:str, schedule_type:str, cron_value:str|None, interval_minutes:int|None, approved_query_id:int|None, message_template_id:int|None, payload:dict|None, next_run_at):
    row=ScheduleJob(name=name, schedule_type=schedule_type, cron_value=cron_value, interval_minutes=interval_minutes, approved_query_id=approved_query_id, message_template_id=message_template_id, payload_json=json.dumps(payload or {}, ensure_ascii=False), next_run_at=next_run_at)
    db.add(row); db.commit(); db.refresh(row); return row

def mark_ran(db:Session, job:ScheduleJob, next_run_at, last_run_at):
    job.last_run_at = last_run_at
    job.next_run_at = next_run_at
    db.commit()
    db.refresh(job)
    return job
