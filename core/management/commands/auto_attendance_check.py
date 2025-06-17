from django.core.management.base import BaseCommand
from django.utils import timezone
import pytz
from core.models import Attendance, Leave, User, Holiday
from datetime import datetime
import calendar

class Command(BaseCommand):
    help = 'Auto-checks attendance and applies leave for absent users, considering holidays and special days'

    def is_second_or_fourth_saturday(self, date):
        """Check if the given date is a second or fourth Saturday"""
        cal = calendar.monthcalendar(date.year, date.month)
        saturdays = [week[5] for week in cal if week[5] != 0]
        return date.day in saturdays[1:3:2]  # Second and fourth Saturdays

    def is_holiday_or_non_working_day(self, date):
        """Check if the given date is a holiday, Sunday, or second/fourth Saturday"""
        # Check if it's Sunday
        if date.weekday() == 6:
            return True, "Sunday"

        # Check if it's second or fourth Saturday
        if date.weekday() == 5 and self.is_second_or_fourth_saturday(date):
            return True, "Second/Fourth Saturday"

        # Check if it's a holiday
        holiday = Holiday.objects.filter(date=date).first()
        if holiday:
            return True, holiday.name

        return False, None

    def handle(self, *args, **options):
        ist = pytz.timezone("Asia/Kolkata")
        now = timezone.now().astimezone(ist)
        today = now.date()
        punch_out_time = now.replace(hour=18, minute=0, second=0, microsecond=0)

        try:
            # Check if today is a non-working day
            is_non_working, reason = self.is_holiday_or_non_working_day(today)
            if is_non_working:
                self.stdout.write(
                    self.style.WARNING(f"Skipping attendance processing: Today is a {reason}")
                )
                return

            users = User.objects.all()
            for user in users:
                try:
                    attendance = Attendance.objects.filter(user=user, date=today).first()
                    
                    if attendance:
                        # Handle existing attendance (auto punch-out)
                        if attendance.punch_in_time and not attendance.punch_out_time:
                            attendance.punch_out_time = punch_out_time
                            attendance.status_punchout = "Early"
                            attendance.status = (
                                "Punched out Early" 
                                if attendance.status_punchin == "On Time" 
                                else "Punched in Late and out Early"
                            )
                            attendance.save()
                            self.stdout.write(
                                self.style.SUCCESS(f"Auto-punched out for {user.username}")
                            )
                    else:
                        # Create LOP leave for absent users on working days
                        Leave.objects.create(
                            user=user,
                            date=today,
                            leave_type="Lose of Pay",
                            reason="Absent without Punch-in",
                            is_approved=False
                        )
                        self.stdout.write(
                            self.style.SUCCESS(f"Created LOP leave for {user.username}")
                        )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error processing user {user.username}: {str(e)}")
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error in attendance processing: {str(e)}")
            )