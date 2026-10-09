from datetime import date, datetime, timedelta, timezone

VIETNAM_TIMEZONE = timezone(timedelta(hours=7))


def local_today(now: datetime | None = None) -> date:
    return (now or datetime.now(VIETNAM_TIMEZONE)).astimezone(VIETNAM_TIMEZONE).date()
