# your_app/management/commands/run_scheduler.py
import os
import django

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')  # Replace 'project.settings' with your actual settings module
django.setup()

from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import BaseCommand
from django.utils import timezone
import pytz

class Command(BaseCommand):
    help = 'Runs the APScheduler for attendance checks'

    def handle(self, *args, **options):
        scheduler = BackgroundScheduler()
        ist = pytz.timezone('Asia/Kolkata')
        
        scheduler.add_job(
            self.run_auto_attendance_check,
            'cron',
            hour=17,  # 11 PM
            minute=38,  # 59 minutes
            timezone=ist
        )
        
        scheduler.start()
        self.stdout.write("Scheduler started. Running auto_attendance_check at 11:59 PM IST daily.")
        
        try:
            while True:
                pass
        except KeyboardInterrupt:
            scheduler.shutdown()
            self.stdout.write("Scheduler stopped.")

    def run_auto_attendance_check(self):
        from django.core.management import call_command
        call_command('auto_attendance_check')