from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import *


admin.site.register(User)
admin.site.register(Task)
admin.site.register(TaskImage)