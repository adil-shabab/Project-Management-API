from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import *


admin.site.register(User)
admin.site.register(Task)
admin.site.register(TaskImage)

admin.site.register(Project)
admin.site.register(ProjectMember)
admin.site.register(ProjectImage)