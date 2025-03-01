# scheduler.py
import os
import django

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')  # Replace 'project.settings' with your actual settings module
django.setup()

from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command
from django.utils import timezone
import pytz

def start_scheduler():
    """Start the APScheduler to run auto_attendance_check at 11:59 PM IST daily."""
    scheduler = BackgroundScheduler()
    ist = pytz.timezone('Asia/Kolkata')
    
    # Schedule the management command to run at 11:59 PM IST every day
    scheduler.add_job(
        call_command,
        'cron',
        args=['auto_attendance_check'],
        trigger='cron',
        hour=17,  # 11 PM
        minute=38,  # 59 minutes
        timezone=ist
    )
    
    # Start the scheduler
    scheduler.start()
    print("Scheduler started. Running auto_attendance_check at 11:59 PM IST daily.")
    
    # Keep the script running (e.g., for testing or development)
    try:
        while True:
            pass
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("Scheduler stopped.")

if __name__ == '__main__':
    start_scheduler()