from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase):
    pass

from app.models.schedule_job_log import ScheduleJobLog
