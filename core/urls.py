# urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/edit/', EditProfileView.as_view(), name='edit-profile'),
    path('edit-avatar/', EditAvatarView.as_view(), name='edit-avatar'),
    path('tasks/create/me/', CreateTaskForMeView.as_view(), name='create_task_me'),
    path('tasks/pending/', UserPendingTasksView.as_view(), name='user_pending_task'),
    path('tasks/<int:task_id>/', TaskDetailView.as_view(), name='task-detail'),


]
