from celery import Celery
from app.core.config import config

connection_link = f"rediss://:{config.redis_token}@{config.redis_host}:{config.redis_port}?ssl_cert_reqs=none"

celery_app = Celery(
    "reminder_worker", broker=connection_link, backend=connection_link
)

# Run every 2 minutes to check for due reminders
celery_app.conf.beat_schedule = {
    'check-due-reminders': {
        'task': 'check_due_reminders',
        'schedule': 120.0,  # Every 2 minutes
    },
}

celery_app.autodiscover_tasks(["app.modules.reminders.tasks"])
