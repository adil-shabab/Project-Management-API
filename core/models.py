from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not username:
            raise ValueError("Username is required")
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'Admin')

        if not extra_fields.get('is_staff'):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get('is_superuser'):
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('Staff', 'Staff'),
        ('Manager', 'Manager'),
        ('Admin', 'Admin'),
    ]

    DEPARTMENT_CHOICES = [
        ('Graphic Designing', 'Graphic Designing'),
        ('Social Media', 'Social Media'),
        ('Digital Marketing', 'Digital Marketing'),
        ('Video Editing', 'Video Editing'),
        ('Web Development', 'Web Development'),
        ('Videography', 'Videography'),
        ('Photography', 'Photography'),
        ('Management', 'Management'),
        ('Content Writing', 'Content Writing'),
    ]

    full_name = models.CharField(max_length=255)
    user_id = models.CharField(max_length=255, null=True, blank=True)
    username = models.CharField(max_length=150, unique=True)
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    position = models.CharField(max_length=150, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Staff')
    avatar = models.ImageField(upload_to='users', blank=True, null=True, verbose_name="Profile Picture")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'full_name']

    def __str__(self):
        return self.username









# Project Model
class Project(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
    ]

    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]


    DEPARTMENT_CHOICES = [
        ('Digital Marketing', 'Digital Marketing'),
        ('Web Development', 'Web Development'),
        ('Graphic Designing', 'Graphic Designing'),
        ('Social Media', 'Social Media'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES, blank=True, null=True)
    client_name = models.CharField(max_length=255)
    due_date = models.DateTimeField()
    start_date = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    team_lead = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects_as_team_lead")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# ProjectMember Model: Link users to projects
class ProjectMember(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=255, default='staff')  # Optional field for role of the member

    def __str__(self):
        return f"{self.user.username} - {self.project.title}"

# ProjectImage Model: To upload images for a project
class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="project_images/")

    def __str__(self):
        return f"Image for {self.project.title}"





class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
    ]


    
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateTimeField()
    start_date = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=6, choices=PRIORITY_CHOICES, default='medium')
    user = models.ForeignKey(User, related_name='tasks', on_delete=models.CASCADE)  # User who the task is assigned to
    assigned_by = models.ForeignKey(User, related_name='assigned_tasks', on_delete=models.CASCADE)  # User who assigned the task
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_ticket = models.BooleanField(default=False)  # Added boolean field for is_ticket
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    review_date = models.DateTimeField(null=True, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="projects", null=True, blank=True)


    def __str__(self):
        return self.title







class TaskStatusChange(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="tasks")
    due_date = models.DateTimeField()
    start_date = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=6, choices=PRIORITY_CHOICES, default='medium')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(null=True, blank=True)
    
    
    
    def __str__(self):
        return self.task.title




class TaskImage(models.Model):
    task = models.ForeignKey(Task, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='task_images/')
    
    def __str__(self):
        return f"Image for {self.task.title}"








class Notification(models.Model):
    """
    Model to store notifications for users.
    """
    NOTIFICATION_TYPE_CHOICES = [
        ('task', 'Task'),
        ('project', 'Project'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")  # Link to a user
    message = models.TextField()  # Notification message content
    created_at = models.DateTimeField(default=timezone.now)  # Timestamp of when the notification was created
    read_status = models.BooleanField(default=False)  # To track whether the notification has been read
    type = models.CharField(max_length=10, choices=NOTIFICATION_TYPE_CHOICES)  # Type of notification (task or project)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="created_notifications")  # Link to the user who created the notification

    class Meta:
        ordering = ['-created_at']  # Order notifications by most recent first

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}..."



class TaskHistory(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=20, choices=Task.STATUS_CHOICES)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)  # Additional notes for status change
    reason = models.TextField(blank=True, null=True)


    def __str__(self):
        return f"{self.task.title} - {self.status} by {self.changed_by.username} at {self.changed_at}"