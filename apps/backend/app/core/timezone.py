from datetime import datetime, timedelta, timezone

# Vietnam Timezone (UTC+7)
VN_TZ = timezone(timedelta(hours=7))


def get_now() -> datetime:
    """Returns the current datetime in Vietnam's timezone (+7)."""
    return datetime.now(VN_TZ)
