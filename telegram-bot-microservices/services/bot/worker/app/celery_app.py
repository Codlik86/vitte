"""
Celery application configuration
"""
from celery import Celery
from celery.schedules import crontab
from app.config import config
from shared.utils import get_logger

logger = get_logger(__name__, config.log_level)

# Create Celery app
celery_app = Celery(
    "vitte_worker",
    broker=config.celery_broker_url,
    backend=config.celery_result_backend
)

# Celery Beat schedule for periodic tasks
beat_schedule = {
    # Cleanup old messages daily at 3 AM UTC
    "cleanup-old-messages-daily": {
        "task": "cleanup.old_messages",
        "schedule": crontab(hour=3, minute=0),
        "args": (50, 30),  # keep_last=50, days_threshold=30
        "options": {
            "expires": 3600,  # Task expires after 1 hour if not executed
        }
    },

    # Cleanup inactive dialogs weekly (every Monday at 4 AM UTC)
    "cleanup-inactive-dialogs-weekly": {
        "task": "cleanup.inactive_dialogs",
        "schedule": crontab(hour=4, minute=0, day_of_week=1),
        "args": (30,),  # days_inactive=30
        "options": {
            "expires": 3600,
        }
    },

    # Generate user stats daily at 6 AM UTC
    "generate-user-stats-daily": {
        "task": "reports.user_stats",
        "schedule": crontab(hour=6, minute=0),
        "options": {
            "expires": 1800,  # Task expires after 30 minutes
        }
    },

    # Generate subscription report daily at 6:30 AM UTC
    "generate-subscription-report-daily": {
        "task": "reports.subscription_report",
        "schedule": crontab(hour=6, minute=30),
        "options": {
            "expires": 1800,
        }
    },

    # Send subscription expiry reminders daily at 10 AM UTC
    "subscription-expiry-reminders-daily": {
        "task": "notifications.subscription_expiry_reminder",
        "schedule": crontab(hour=10, minute=0),
        "args": (3,),  # days_before=3 (remind 3 days before expiration)
        "options": {
            "expires": 3600,
        }
    },

    # Check inactive dialogs and send notifications every 10 minutes
    "check-inactive-dialogs-every-10min": {
        "task": "notifications.check_inactive_dialogs",
        "schedule": 600.0,  # Every 10 minutes (600 seconds)
        "options": {
            "expires": 300,  # Task expires after 5 minutes
        }
    },

    # Check and send broadcasts to new users every 5 minutes
    "check-new-user-broadcasts-every-5min": {
        "task": "broadcast.check_new_user_broadcasts",
        "schedule": 300.0,  # Every 5 minutes (300 seconds)
        "options": {
            "expires": 240,  # Task expires after 4 minutes
        }
    },
}

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=config.celery_task_time_limit,
    task_soft_time_limit=config.celery_task_soft_time_limit,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Beat schedule
    beat_schedule=beat_schedule,
    # RedBeat scheduler - хранит schedule в Redis вместо файла
    redbeat_redis_url=config.celery_broker_url,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.tasks"])

logger.info("Celery app configured with beat schedule")


# Initialize RedBeat schedule entries on import
def init_redbeat_entries():
    """Initialize RedBeat entries from beat_schedule config"""
    try:
        from redbeat import RedBeatSchedulerEntry

        logger.info(f"Initializing RedBeat schedule entries ({len(beat_schedule)} tasks)...")

        created_count = 0
        for name, config in beat_schedule.items():
            try:
                # Create/update entry (will overwrite if exists)
                entry = RedBeatSchedulerEntry(
                    name=name,
                    task=config['task'],
                    schedule=config['schedule'],
                    args=config.get('args', ()),
                    kwargs=config.get('kwargs', {}),
                    options=config.get('options', {}),
                    app=celery_app
                )
                entry.save()
                created_count += 1

                schedule_info = str(config['schedule'])
                logger.info(f"✓ Registered RedBeat entry: {name} -> {config['task']} ({schedule_info})")

            except Exception as e:
                logger.error(f"✗ Failed to create RedBeat entry '{name}': {e}", exc_info=True)
                continue

        logger.info(f"RedBeat schedule initialized: {created_count}/{len(beat_schedule)} entries registered")

    except ImportError:
        # RedBeat not available, skip initialization
        logger.warning("RedBeat not installed, skipping schedule initialization")
    except Exception as e:
        logger.error(f"RedBeat initialization failed: {e}", exc_info=True)


# Initialize entries when module is imported by beat
init_redbeat_entries()
