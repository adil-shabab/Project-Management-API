from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

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
        ('Digital Marketing', 'Digital Marketing'),
        ('Web Development', 'Web Development'),
        ('Graphic Designing', 'Graphic Designing'),
        ('Social Media', 'Social Media'),
    ]

    full_name = models.CharField(max_length=255)
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

    def __str__(self):
        return self.title




class TaskImage(models.Model):
    task = models.ForeignKey(Task, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='task_images/')
    
    def __str__(self):
        return f"Image for {self.task.title}"