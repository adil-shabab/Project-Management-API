# your_app/management/commands/daily_task.py
from django.core.management.base import BaseCommand
from core.models import User
from core.models import Leave, Attendance, Holiday  # Adjust import based on your structure
import pytz
from django.utils import timezone

class Command(BaseCommand):
    help = 'Runs daily task to handle attendance and leaves'

    def handle(self, *args, **options):
        ist = pytz.timezone("Asia/Kolkata")
        now = timezone.now().astimezone(ist)
        today = now.date()
        punch_out_time = now.replace(hour=18, minute=0, second=0, microsecond=0)

        users = User.objects.all()
        for user in users:
            attendance = Attendance.objects.filter(user=user, date=today).first()
            if attendance:
                if attendance.punch_in_time and not attendance.punch_out_time:
                    attendance.punch_out_time = punch_out_time
                    attendance.status_punchout = "Early"
                    attendance.status = "Punched out Early" if attendance.status_punchin == "On Time" else "Punched in Late"
                    attendance.save()
                    self.stdout.write(f"Auto-punched out {user.username}")
            else:
                # Check if there's an approved leave for this user on this date
                approved_leave = Leave.objects.filter(
                    user=user,
                    date=today,
                    status='Approved'
                ).exists()
                holidays = Holiday.objects.filter(
                    date=today,
                ).exists()
                
                if not approved_leave:
                    if not holidays:
                        # Create Lose of Pay leave only if no approved leave exists
                        Leave.objects.create(
                            user=user,
                            date=today,
                            status='Approved',
                            leave_type="Full Day - Lose of Pay",  # Updated to match choices
                            reason="Absent without Punch-in"
                        )
                        self.stdout.write(f"Created Lose of Pay Leave for {user.username}")
                else:
                    self.stdout.write(f"Approved leave found for {user.username}, no action taken")