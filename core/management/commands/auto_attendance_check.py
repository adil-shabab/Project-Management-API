from django.core.management.base import BaseCommand
from django.utils import timezone
import pytz
from core.models import Attendance, Leave, User

class Command(BaseCommand):
    help = 'Auto-checks attendance and applies leave for absent users'

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
                Leave.objects.create(
                    user=user,
                    date=today,
                    leave_type="Lose of Pay",
                    reason="Absent without Punch-in"
                )
                self.stdout.write(f"Created Leave for {user.username}")