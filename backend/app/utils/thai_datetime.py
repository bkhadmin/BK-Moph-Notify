from datetime import datetime, timedelta, timezone

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน",
    "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม",
    "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

BANGKOK_TZ = timezone(timedelta(hours=7))

def bangkok_now() -> datetime:
    return datetime.now(BANGKOK_TZ)

def format_thai_date(dt: datetime) -> str:
    if not dt:
        return ""
    day = dt.day
    month = THAI_MONTHS[dt.month]
    year = dt.year + 543
    return f"{day} {month} {year}"

def format_thai_time(dt: datetime) -> str:
    if not dt:
        return ""
    return dt.strftime("%H.%M") + " น."

def format_thai_datetime(dt: datetime) -> str:
    if not dt:
        return ""
    return f"{format_thai_date(dt)} เวลา {dt.strftime('%H.%M')} น."
