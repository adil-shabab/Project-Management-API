from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

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

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'Admin')
        return self.create_user(username, email, password, **extra_fields)

class User(AbstractBaseUser):
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
    position = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Staff')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name']

    def __str__(self):
        return self.username
