"""Tasks module"""
from app.tasks.cleanup import cleanup_old_messages, cleanup_inactive_dialogs, test_task
from app.tasks.reports import generate_user_stats, generate_subscription_report
from app.tasks.notifications import send_subscription_expiry_reminder, send_admin_alert
from app.tasks.memory import index_message, delete_user_memories, memory_health_check

__all__ = [
    # Cleanup tasks
    "cleanup_old_messages",
    "cleanup_inactive_dialogs",
    "test_task",
    # Report tasks
    "generate_user_stats",
    "generate_subscription_report",
    # Notification tasks
    "send_subscription_expiry_reminder",
    "send_admin_alert",
    # Memory tasks
    "index_message",
    "delete_user_memories",
    "memory_health_check",
]
