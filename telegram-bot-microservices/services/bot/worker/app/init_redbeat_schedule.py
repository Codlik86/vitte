"""
Initialize RedBeat schedule entries from beat_schedule config

This script creates RedBeat entries in Redis from the beat_schedule
configuration. Run this once after switching to RedBeat scheduler.
"""
import sys
from redbeat import RedBeatSchedulerEntry
from celery.schedules import crontab
from app.celery_app import celery_app, beat_schedule


def init_redbeat_schedule():
    """Create RedBeat entries from beat_schedule config"""
    print("Initializing RedBeat schedule from beat_schedule config...")

    for name, config in beat_schedule.items():
        try:
            # Check if entry already exists
            try:
                existing = RedBeatSchedulerEntry.from_key(
                    f'redbeat:{name}',
                    app=celery_app
                )
                print(f"✓ Entry '{name}' already exists, skipping")
                continue
            except KeyError:
                # Entry doesn't exist, create it
                pass

            # Create new entry
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

            schedule_type = "crontab" if isinstance(config['schedule'], crontab) else f"{config['schedule']}s"
            print(f"✓ Created entry '{name}': {config['task']} ({schedule_type})")

        except Exception as e:
            print(f"✗ Error creating entry '{name}': {e}")
            continue

    print("\nRedBeat schedule initialized successfully!")
    print(f"Total entries: {len(beat_schedule)}")


if __name__ == "__main__":
    init_redbeat_schedule()
