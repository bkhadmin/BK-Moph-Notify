from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def parse_next_run(schedule_type:str, cron_value:str|None, interval_minutes:int|None, base:datetime|None=None):
    now = base or datetime.now()
    if schedule_type == 'once':
        if not cron_value:
            return None
        return datetime.fromisoformat(cron_value.replace('T',' '))
    if schedule_type == 'interval_minutes':
        return now + timedelta(minutes=max(interval_minutes or 1, 1))
    if schedule_type == 'daily':
        # cron_value = HH:MM
        hh, mm = (cron_value or '06:00').split(':')
        candidate = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
    if schedule_type == 'monthly':
        # cron_value = DD HH:MM e.g. 1 06:00
        day_str, time_str = (cron_value or '1 06:00').split(' ', 1)
        hh, mm = time_str.split(':')
        day = int(day_str)
        candidate = now.replace(day=min(day,28), hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if candidate <= now:
            candidate = candidate + relativedelta(months=1)
            candidate = candidate.replace(day=min(day,28))
        return candidate
    return None

def next_after_run(schedule_type:str, cron_value:str|None, interval_minutes:int|None, last_run_at:datetime):
    if schedule_type == 'once':
        return None
    return parse_next_run(schedule_type, cron_value, interval_minutes, base=last_run_at)
