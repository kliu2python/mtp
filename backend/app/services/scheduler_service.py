"""
Test Scheduler Service for automated test execution
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from pytz import timezone as pytz_timezone

from app.core.database import SessionLocal
from app.models.test_schedule import TestSchedule, ScheduleStatus
from app.services.test_executor import TestExecutor

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing automated test schedules"""

    def __init__(self):
        """Initialize the scheduler service"""
        self.scheduler = AsyncIOScheduler(
            jobstores={'default': MemoryJobStore()},
            timezone=pytz_timezone('UTC')
        )
        self.test_executor = None
        self.running = False

    async def start(self):
        """Start the scheduler service"""
        if self.running:
            logger.warning("Scheduler is already running")
            return

        logger.info("Starting Test Scheduler Service...")

        # Initialize test executor
        from app.services.test_executor import test_executor
        self.test_executor = test_executor

        # Load all active schedules from database
        await self.load_schedules()

        # Start the scheduler
        self.scheduler.start()
        self.running = True

        logger.info("✅ Test Scheduler Service started successfully")

    async def stop(self):
        """Stop the scheduler service"""
        if not self.running:
            return

        logger.info("Stopping Test Scheduler Service...")
        self.scheduler.shutdown(wait=True)
        self.running = False
        logger.info("✅ Test Scheduler Service stopped")

    async def load_schedules(self):
        """Load all active schedules from database and add them to scheduler"""
        db = SessionLocal()
        try:
            schedules = db.query(TestSchedule).filter(
                TestSchedule.enabled == True,
                TestSchedule.status == ScheduleStatus.ACTIVE
            ).all()

            logger.info(f"Loading {len(schedules)} active schedules...")

            for schedule in schedules:
                try:
                    await self.add_job(schedule)
                    logger.info(f"Loaded schedule: {schedule.name} ({schedule.cron_expression})")
                except Exception as e:
                    logger.error(f"Failed to load schedule {schedule.name}: {e}")

            logger.info(f"✅ Loaded {len(schedules)} schedules")
        finally:
            db.close()

    async def add_job(self, schedule: TestSchedule):
        """
        Add a scheduled job to the scheduler

        Args:
            schedule: TestSchedule model instance
        """
        job_id = str(schedule.id)

        # Remove existing job if present
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        # Parse cron expression
        cron_parts = schedule.cron_expression.split()
        if len(cron_parts) != 5:
            raise ValueError(f"Invalid cron expression: {schedule.cron_expression}")

        minute, hour, day, month, day_of_week = cron_parts

        # Create cron trigger
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone=pytz_timezone(schedule.timezone or 'UTC')
        )

        # Add job to scheduler
        self.scheduler.add_job(
            func=self._execute_scheduled_test,
            trigger=trigger,
            args=[str(schedule.id)],
            id=job_id,
            name=schedule.name,
            replace_existing=True
        )

        # Update next_run_at in database
        next_run = self.scheduler.get_job(job_id).next_run_time
        db = SessionLocal()
        try:
            db_schedule = db.query(TestSchedule).filter(TestSchedule.id == schedule.id).first()
            if db_schedule:
                db_schedule.next_run_at = next_run
                db.commit()
        finally:
            db.close()

        logger.info(f"Added scheduled job: {schedule.name}, next run: {next_run}")

    async def remove_job(self, schedule_id: str):
        """
        Remove a scheduled job from the scheduler

        Args:
            schedule_id: Schedule UUID
        """
        job_id = str(schedule_id)

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed scheduled job: {job_id}")

    async def _execute_scheduled_test(self, schedule_id: str):
        """
        Execute a scheduled test

        Args:
            schedule_id: Schedule UUID
        """
        db = SessionLocal()
        try:
            # Get schedule from database
            schedule = db.query(TestSchedule).filter(TestSchedule.id == schedule_id).first()
            if not schedule:
                logger.error(f"Schedule not found: {schedule_id}")
                return

            if not schedule.enabled or schedule.status != ScheduleStatus.ACTIVE:
                logger.warning(f"Schedule {schedule.name} is not active, skipping execution")
                return

            logger.info(f"🚀 Executing scheduled test: {schedule.name}")

            # Update last_run_at
            schedule.last_run_at = datetime.utcnow()
            schedule.last_run_status = "running"
            schedule.total_runs += 1
            db.commit()

            # Prepare test configuration
            test_config = schedule.test_config.copy()
            test_config['name'] = f"[Scheduled] {schedule.name}"
            test_config['scheduled'] = True
            test_config['schedule_id'] = str(schedule.id)

            # Add VM and device IDs if specified
            if schedule.vm_ids:
                test_config['vm_ids'] = schedule.vm_ids
            if schedule.device_ids:
                test_config['device_ids'] = schedule.device_ids
            if schedule.apk_id:
                test_config['apk_id'] = str(schedule.apk_id)

            # Execute test
            try:
                # Use test executor to run the test
                task_id = await self.test_executor.execute_test(test_config)

                # Update schedule with task ID
                schedule.last_run_task_id = task_id
                schedule.last_run_status = "queued"
                db.commit()

                logger.info(f"✅ Scheduled test queued: {schedule.name}, task_id: {task_id}")

                # Send notification (in background)
                if schedule.notify_on_success:
                    asyncio.create_task(
                        self._send_notification(schedule, "started", task_id)
                    )

            except Exception as e:
                logger.error(f"Failed to execute scheduled test {schedule.name}: {e}")

                schedule.last_run_status = "failed"
                schedule.failed_runs += 1
                db.commit()

                # Send failure notification
                if schedule.notify_on_failure:
                    asyncio.create_task(
                        self._send_notification(schedule, "failed", error=str(e))
                    )

            # Update next_run_at
            job = self.scheduler.get_job(str(schedule.id))
            if job and job.next_run_time:
                schedule.next_run_at = job.next_run_time
                db.commit()

        except Exception as e:
            logger.error(f"Error in scheduled test execution: {e}")
        finally:
            db.close()

    async def _send_notification(
        self,
        schedule: TestSchedule,
        status: str,
        task_id: str = None,
        error: str = None
    ):
        """
        Send notification about test execution

        Args:
            schedule: TestSchedule instance
            status: Test status ("started", "completed", "failed")
            task_id: Optional task ID
            error: Optional error message
        """
        try:
            # Import notification service
            from app.services.notification_service import send_email_notification, send_teams_notification

            # Prepare message
            if status == "started":
                subject = f"Scheduled Test Started: {schedule.name}"
                message = f"Scheduled test '{schedule.name}' has been queued.\nTask ID: {task_id}"
            elif status == "completed":
                subject = f"Scheduled Test Completed: {schedule.name}"
                message = f"Scheduled test '{schedule.name}' completed successfully.\nTask ID: {task_id}"
            elif status == "failed":
                subject = f"Scheduled Test Failed: {schedule.name}"
                message = f"Scheduled test '{schedule.name}' failed.\nError: {error}"
            else:
                subject = f"Scheduled Test Update: {schedule.name}"
                message = f"Status: {status}"

            # Send email notifications
            if schedule.notification_emails:
                for email in schedule.notification_emails:
                    try:
                        await send_email_notification(email, subject, message)
                    except Exception as e:
                        logger.error(f"Failed to send email to {email}: {e}")

            # Send Teams notification
            if schedule.notification_teams_webhook:
                try:
                    await send_teams_notification(
                        schedule.notification_teams_webhook,
                        subject,
                        message
                    )
                except Exception as e:
                    logger.error(f"Failed to send Teams notification: {e}")

        except Exception as e:
            logger.error(f"Error sending notification: {e}")

    def get_job_info(self, schedule_id: str) -> Optional[dict]:
        """
        Get information about a scheduled job

        Args:
            schedule_id: Schedule UUID

        Returns:
            Job information dictionary or None
        """
        job = self.scheduler.get_job(str(schedule_id))
        if not job:
            return None

        return {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        }


# Global scheduler instance
scheduler_service = SchedulerService()
