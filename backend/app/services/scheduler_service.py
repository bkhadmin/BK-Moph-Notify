from datetime import datetime, timedelta

def parse_next_run(schedule_type, cron_value=None, interval_minutes=None, base=None):
    base = base or datetime.now()

    if schedule_type in ("once", "run_once"):
        if not cron_value:
            return base
        raw = str(cron_value).strip().replace("T", " ")
        return datetime.fromisoformat(raw)

    if schedule_type in ("every_minutes", "interval_minutes"):
        minutes = int(interval_minutes or 5)
        return base + timedelta(minutes=minutes)

    if schedule_type in ("daily_time", "every_day_time"):
        raw = (cron_value or "").strip()
        if "." in raw and ":" not in raw:
            raw = raw.replace(".", ":")
        hh, mm = raw.split(":", 1)
        candidate = base.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if candidate <= base:
            candidate = candidate + timedelta(days=1)
        return candidate

    if schedule_type in ("hourly",):
        return base.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    if schedule_type in ("monthly",):
        return base + timedelta(days=30)

    return base + timedelta(minutes=int(interval_minutes or 5))

def scheduler_now():
    return datetime.now()
